#!/usr/bin/env python3
"""Conan test_package — compartment 1.3 (command-line tools).

Runs test_compartment.py against the installed compartment-user and
compartment-root binaries (three real CLI checks) and emits the HMBS
evidence markers. The upstream quick-suite result persisted by the main
recipe (res/upstream_test_result.json) is re-emitted here so every
preflight round carries upstream evidence even when the main build step
is skipped from cache.
"""

import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class CompartmentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def _writable_tmpdir(self):
        for var in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                try:
                    os.makedirs(value, exist_ok=True)
                    return value
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, ".tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _probe_help(self, bin_path):
        try:
            proc = subprocess.run(
                [bin_path, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=15,
            )
            return proc.returncode, proc.stdout or ""
        except Exception as exc:
            return -999, "probe-error=%s" % exc

    def _maybe_sign(self, bin_path):
        if self.settings.os != "OHOS" or not os.path.isfile(bin_path):
            return bin_path
        # Package binaries are already signed at package() time. Probe the
        # installed binary in place first: when --help runs, no copy or
        # re-sign is needed at all. This avoids a strip+resign rewrite cycle
        # on the tmp copy that can leave a corrupt binary (observed as
        # SIGSYS with empty output on compartment-user while the untouched
        # build-tree binary and compartment-root both run fine).
        rc, out = self._probe_help(bin_path)
        try:
            size0 = os.path.getsize(bin_path)
        except OSError:
            size0 = -1
        self.output.info(
            "pre-sign probe %s: rc=%s size=%s has_usage=%s out=%r"
            % (bin_path, rc, size0, ("Usage:" in out), out[:120])
        )
        if rc == 0 and "Usage:" in out:
            return bin_path
        tmpdir = self._writable_tmpdir()
        signed_copy = os.path.join(tmpdir, os.path.basename(bin_path) + ".signed")
        try:
            shutil.copy2(bin_path, signed_copy)
            bin_path = signed_copy
        except OSError:
            pass
        # Sign the copy directly WITHOUT llvm-objcopy stripping: the copy
        # preserves the package-time signature and the sign tool handles
        # re-signing. Stripping is only a last resort if direct signing
        # fails (it rewrites the ELF and risks corruption).
        signed = False
        sign_err = ""
        for tool in (
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool") or "binary-sign-tool",
        ):
            try:
                result = subprocess.run(
                    [tool, "sign", "-inFile", bin_path, "-outFile", bin_path, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15,
                )
                sign_err = (result.stderr or b"").decode("utf-8", "replace")[:160] if isinstance(result.stderr, bytes) else str(result.stderr or "")[:160]
                if result.returncode == 0:
                    signed = True
                    self.output.info("signed %s with %s" % (bin_path, tool))
                    break
                self.output.warning("sign with %s rc=%s err=%r" % (tool, result.returncode, sign_err))
            except Exception as exc:
                self.output.warning("sign with %s raised %s" % (tool, exc))
                continue
        if not signed:
            # Last resort: strip stale signature section once, then re-sign.
            for tool in (
                "/data/service/hnp/bin/llvm-objcopy",
                shutil.which("llvm-objcopy") or "llvm-objcopy",
            ):
                try:
                    subprocess.run(
                        [tool, "--remove-section", ".codesign", bin_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=10,
                    )
                    break
                except Exception:
                    continue
            for tool in (
                "/data/service/hnp/bin/binary-sign-tool",
                shutil.which("binary-sign-tool") or "binary-sign-tool",
            ):
                try:
                    result = subprocess.run(
                        [tool, "sign", "-inFile", bin_path, "-outFile", bin_path, "-selfSign", "1"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                        timeout=15,
                    )
                    if result.returncode == 0:
                        signed = True
                        self.output.info("signed %s with %s (after strip)" % (bin_path, tool))
                        break
                except Exception:
                    continue
        try:
            os.chmod(bin_path, 0o755)
        except OSError:
            pass
        try:
            size1 = os.path.getsize(bin_path)
        except OSError:
            size1 = -1
        rc2, out2 = self._probe_help(bin_path)
        self.output.info(
            "post-sign probe %s: rc=%s size=%s->%s has_usage=%s out=%r"
            % (bin_path, rc2, size0, size1, ("Usage:" in out2), out2[:120])
        )
        return bin_path

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        user_bin = os.path.join(dep.package_folder, "bin", "compartment-user")
        root_bin = os.path.join(dep.package_folder, "bin", "compartment-root")
        for candidate in (user_bin, root_bin):
            if not os.path.isfile(candidate):
                raise ConanException("expected binary missing: %s" % candidate)
        user_bin = self._maybe_sign(user_bin)
        root_bin = self._maybe_sign(root_bin)

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        tmpdir = self._writable_tmpdir()
        script = os.path.join(self.recipe_folder, "test_compartment.py")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        inner = '"%s" "%s" "%s" "%s" > "%s" 2>&1' % (sys.executable, script, user_bin, root_bin, logfile)
        if shutil.which("timeout"):
            cmd = "timeout 60 %s" % inner
        else:
            cmd = inner
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_compartment.py log:\n" + "\n".join(out.splitlines()[-12:]))

        marker_cmd = "%s %s <compartment-user> <compartment-root>" % (sys.executable, script)
        match = re.search(r"RESULT:\s*(\d+)\s+passed,\s*(\d+)\s+failed", out)
        if not match:
            raise ConanException("test_compartment.py produced no RESULT line")
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(
                {
                    "executed": True,
                    "passed": ok,
                    "command": marker_cmd,
                    "discovered": discovered,
                    "passedCount": passed,
                },
                ensure_ascii=False,
            )
        )
        if not ok:
            raise RuntimeError("consumer test failed: %d passed, %d failed" % (passed, failed))

        emitted = False
        for candidate in (
            os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
            os.path.join(dep.package_folder, "upstream_test_result.json"),
        ):
            if os.path.isfile(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
                emitted = True
                break
        if not emitted:
            raise ConanException("upstream_test_result.json missing from package res/")
