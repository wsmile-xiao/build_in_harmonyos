#!/usr/bin/env python3
"""Test package for ticker 1.16.

Runs the packaged bin/ticker through two shell harnesses (invoked via the
resolved Bourne shell, default /bin/sh; the shebang cannot be trusted on
HMDFS):

* test_ticker.sh — 3 functional cases, all settling inside Parse_Params()
  before ticker touches the terminal (short help == upstream autopkgtest
  command, long help, missing-message negative path).
* test_ticker_ohos.sh — 2 HarmonyOS-specific cases: AArch64 ELF machine and
  libslang NEEDED linkage (file inspection, needs no terminal).

Case counts come from each script's own `SUMMARY: pass=N fail=M` line — a
single deterministic source per script. The scripts exit non-zero unless
every case passes, so a silent skip cannot be mistaken for a pass.
"""

import os
import platform
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException

# test_ticker.sh cases + test_ticker_ohos.sh cases.
EXPECTED_CASES = 5


class TickerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _qemu(self):
        """Empty when running natively on AArch64, else qemu-aarch64 path."""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return ""
        qemu = shutil.which("qemu-aarch64")
        if qemu is None:
            raise ConanException("qemu-aarch64 is required to run AArch64 binaries here")
        return qemu

    @staticmethod
    def _shell():
        """Resolve a working Bourne shell (profile bash may be missing)."""
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL"),
                     "/bin/sh"):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        found = shutil.which("sh")
        if found:
            return found
        return "/bin/sh"

    @staticmethod
    def _read_summary(log_path):
        """Parse the harness's own SUMMARY line (sole count source)."""
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        match = re.search(r"(?m)^SUMMARY: pass=(\d+) fail=(\d+)$", content)
        if not match:
            raise ConanException(f"no SUMMARY line in {log_path}")
        return content, int(match.group(1)), int(match.group(2))

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        ticker_bin = os.path.join(pkg_folder, "bin", "ticker")
        qemu = self._qemu()
        shell = self._shell()
        self.output.info(f"using shell: {shell}")

        total_pass = 0
        total_fail = 0
        all_ok = True
        for script in ("test_ticker.sh", "test_ticker_ohos.sh"):
            script_path = os.path.join(self.recipe_folder, script)
            log_path = os.path.join(self.build_folder, script + ".log")
            rc = self.run(f'"{shell}" "{script_path}" "{ticker_bin}" "{qemu}"'
                          f' > "{log_path}" 2>&1',
                          env="conanrun", ignore_errors=True)
            try:
                content, passed, failed = self._read_summary(log_path)
            except ConanException as exc:
                self.output.error(str(exc))
                all_ok = False
                continue
            print(content, end="")
            total_pass += passed
            total_fail += failed
            if rc != 0 or failed != 0:
                all_ok = False

        # Self-check, no number patching: the two SUMMARY lines must add up
        # to exactly the declared case count.
        if total_pass + total_fail != EXPECTED_CASES:
            self.output.error(
                f"case count mismatch: pass={total_pass} fail={total_fail}, "
                f"expected {EXPECTED_CASES}")
            all_ok = False

        print(f'HMBS_TEST_PACKAGE_RESULT={{"executed":true,'
              f'"passed":{str(all_ok).lower()},'
              f'"command":"{shell} test_ticker.sh + {shell} test_ticker_ohos.sh",'
              f'"discovered":{EXPECTED_CASES},"passedCount":{total_pass}}}')
        if not all_ok:
            raise ConanException(
                f"test_package failed: pass={total_pass} fail={total_fail}")
