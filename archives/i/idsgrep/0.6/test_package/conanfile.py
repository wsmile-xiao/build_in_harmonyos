#!/usr/bin/env python3
"""Conan test_package — idsgrep 0.6 (command-line tool).

idsgrep is an application package (bin/idsgrep), so build() does no
linking; test() executes test_idsgrep.sh against the installed binary for
6 content checks (inventory, -V banner, structural query, PCRE query,
missing-dictionary diagnostic, unparsable-query exit code), satisfying L0d (test() holds self.run) and R34 (the
packaged binary is really executed). Every positive case asserts non-empty
output plus exact expected content, so loader errors or empty fixtures
cannot masquerade as passes (toybox-tar lesson).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
- HMBS_UPSTREAM_TEST_RESULT: re-emitted from res/upstream_test_result.json
  persisted by the main recipe's build() (which parses test-suite.log, the
  single deterministic source). Re-emission here covers cache-hit rounds
  where build() output is skipped ("Already installed!").
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


class IdsgrepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Tool package: no library to link; functional checks run in test().
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
        idsgrep_bin = os.path.join(
            self.dependencies["idsgrep"].package_folder, "bin", "idsgrep"
        )
        if not os.path.isfile(idsgrep_bin):
            raise ConanException(
                "idsgrep binary not found in package: %s" % idsgrep_bin
            )
        if self.settings.os == "OHOS":
            idsgrep_bin = self._writable_signed_copy(idsgrep_bin)

        shell = "/bin/sh"
        for _cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(_cand):
                    shell = _cand
                    break
            except OSError:
                continue
        else:
            shell = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or "/bin/sh"
            )
            # Never reuse the poisoned profile bash when it is missing.
            try:
                if "/" in shell and not os.path.isfile(shell):
                    shell = "/bin/sh"
            except OSError:
                shell = "/bin/sh"
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_idsgrep.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "IDSGREP_BIN=%s" % shlex.quote(idsgrep_bin),
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            "timeout 90" if (
                shutil.which("timeout")
                or os.path.isfile("/data/service/hnp/bin/timeout")
            ) else "exec",
            shlex.quote(shell),
            shlex.quote(test_script),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_idsgrep.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_idsgrep.sh produced no RESULT line — harness broken"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s test_idsgrep.sh (IDSGREP_BIN=<pkg>/bin/idsgrep)"
                       % shell,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_idsgrep.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Re-emit the upstream verdict persisted by the main recipe so the
        # evidence survives cache-hit rounds. Numbers are read, not guessed.
        pkg = self.dependencies["idsgrep"].package_folder
        persisted = os.path.join(pkg, "res", "upstream_test_result.json")
        if os.path.isfile(persisted):
            with open(persisted, "r", encoding="utf-8") as f:
                upstream_marker = json.load(f)
        else:
            upstream_marker = {
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": 25,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "res/upstream_test_result.json missing from idsgrep "
                    "package; refusing to invent upstream counts"
                ),
            }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("idsgrep functional test_package passed")
