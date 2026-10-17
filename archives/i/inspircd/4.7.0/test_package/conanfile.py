#!/usr/bin/env python3
"""Conan test_package — inspircd 4.7.0 (server daemon application).

inspircd is an application package (bin/inspircd + modules/*.so), so
build() does no linking; test() executes test_inspircd.sh against the
installed server for 5 content checks (binary inventory, --version
banner, TCP listen, real IRC NICK/USER -> 001 handshake, clean-shutdown
port release), satisfying L0d (test() holds self.run) and R34 (the
packaged binary is really executed, handshake bytes verified).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (single
  deterministic source; the script exits non-zero unless all pass).
- HMBS_UPSTREAM_TEST_RESULT: re-emitted from res/upstream_test_result.json
  persisted by the main recipe's build() (status no_tests with audit
  reason). Re-emission here covers cache-hit rounds where build() output
  is skipped ("Already installed!").
"""

import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class InspircdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Server package: no library to link; functional checks run in test().
        pass

    def _writable_signed_copy(self, binary):
        """Copy the packaged binary to writable TMPDIR and self-sign it.

        The conan cache may sit on read-only HMDFS (hardlink/chmod
        unsupported); signing the package copy in place fails silently and
        the HongMeng kernel SIGKILLs unsigned binaries on exec. Signing a
        writable copy (backuppc-rsync precedent) avoids that.
        """
        writable_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            writable_tmp = self.build_folder
        signed_copy = os.path.join(
            writable_tmp, os.path.basename(binary) + ".signed"
        )
        try:
            shutil.copy2(binary, signed_copy)
            self.output.info(
                "OHOS test: copied %s -> writable %s for signing"
                % (binary, signed_copy)
            )
            binary = signed_copy
        except Exception as exc:
            self.output.warning(
                "OHOS test: copy to writable tmp failed (%s)" % exc
            )
            return binary
        for tool in (
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "llvm-objcopy",
        ):
            try:
                subprocess.run(
                    [tool, "--remove-section", ".codesign", binary],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
                break
            except Exception:
                continue
        signed = False
        for tool in (
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool") or "binary-sign-tool",
        ):
            try:
                proc = subprocess.run(
                    [tool, "sign", "-inFile", binary,
                     "-outFile", binary, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15,
                )
                if proc.returncode == 0:
                    self.output.info(
                        "OHOS self-signed test binary %s with %s"
                        % (binary, tool)
                    )
                    signed = True
                    break
                self.output.warning(
                    "sign tool %s returned %s" % (tool, proc.returncode)
                )
            except Exception as exc:
                self.output.warning("sign tool %s exception: %s" % (tool, exc))
                continue
        if not signed:
            self.output.warning(
                "OHOS signing failed for %s (will try exec anyway)" % binary
            )
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass
        return binary

    def test(self):
        pkg = self.dependencies["inspircd"].package_folder
        inspircd_bin = os.path.join(pkg, "bin", "inspircd")
        if not os.path.isfile(inspircd_bin):
            raise ConanException(
                "inspircd binary not found in package: %s" % inspircd_bin
            )
        moddir = os.path.join(pkg, "modules")
        if not os.path.isdir(moddir):
            raise ConanException(
                "inspircd modules dir missing in package: %s" % moddir
            )
        if self.settings.os == "OHOS":
            inspircd_bin = self._writable_signed_copy(inspircd_bin)

        shell = "/bin/sh"
        for _cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(_cand):
                    shell = _cand
                    break
            except OSError:
                continue
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_inspircd.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_prefix = "%s %s %s %s %s" % (
            "INSPIRCD_BIN=%s" % shlex.quote(inspircd_bin),
            "INSPIRCD_MODDIR=%s" % shlex.quote(moddir),
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
        )
        cmd = "%s %s > %s 2>&1" % (
            shlex.quote(shell),
            shlex.quote(test_script),
            shlex.quote(logfile),
        )
        # GNU timeout execs its first argument directly and does not
        # understand shell VAR=val prefixes, so `timeout 300 VAR=x sh`
        # fails with "failed to run command 'VAR=x': No such file".
        # Route assignments through `env` when timeout is present.
        timeout_bin = shutil.which("timeout")
        if not timeout_bin and os.path.isfile("/data/service/hnp/bin/timeout"):
            timeout_bin = "/data/service/hnp/bin/timeout"
        if timeout_bin:
            inner = "%s 300 env %s %s" % (
                shlex.quote(timeout_bin), env_prefix, cmd)
        else:
            inner = "%s %s" % (env_prefix, cmd)
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_inspircd.sh log:\n" + "\n".join(out.splitlines()[-25:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_inspircd.sh produced no RESULT line — harness broken"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s test_inspircd.sh (INSPIRCD_BIN=<pkg>/bin/inspircd, live 001 handshake)" % shell,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_inspircd.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Re-emit the upstream verdict persisted by the main recipe so the
        # evidence survives cache-hit rounds. Numbers are read, not guessed.
        persisted = os.path.join(pkg, "res", "upstream_test_result.json")
        if os.path.isfile(persisted):
            with open(persisted, "r", encoding="utf-8") as f:
                upstream_marker = json.load(f)
        else:
            upstream_marker = {
                "status": "failed",
                "framework": "inspircd-configure",
                "command": "./configure --disable-auto-extras",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "res/upstream_test_result.json missing from inspircd "
                    "package; refusing to invent upstream counts"
                ),
            }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("inspircd functional test_package passed")
