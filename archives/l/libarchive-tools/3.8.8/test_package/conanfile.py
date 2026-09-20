#!/usr/bin/env python3
"""Conan test_package — libarchive-tools 3.8.8.

Functional coverage (R34: executes the packaged binaries and links the
shipped libarchive API):
- test_bsdtar.sh: 5 real assertions (bsdtar/bsdcpio --version, archive
  create non-empty, list, extract + cmp round-trip).
- test_libarchive_api.c: in-memory write/read round-trip through the
  shipped libarchive (ustar format, pathname/size/content asserts).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibarchiveToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libarchive-tools"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} test_libarchive_api.c -o test_libarchive_api "
            f"{inc_flags} {lib_flags} -larchive",
            env="conanbuild")

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skipping runtime tests")
            tp_skip = {
                "executed": False,
                "passed": False,
                "command": "skipped (cross-compiling)",
                "discovered": 6,
                "passedCount": 0,
            }
            print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_skip)}")
            ut_skip = {
                "status": "no_tests",
                "framework": "autotools",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "cross-compiling: upstream make check runs at build time on the target",
            }
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_skip)}")
            return

        # HMBS shell_getcwd: use the HMBS-injected SHELL/CONFIG_SHELL
        # (/bin/sh); the HNP bash cannot getcwd on HMFS/HMDFS workdirs.
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get(
            "SHELL", "/bin/sh")
        discovered = 6
        passed = 0
        try:
            self.run(f"{bash} test_bsdtar.sh", env="conanrun")
            passed += 5
        except Exception as exc:
            self.output.error(f"test_bsdtar.sh failed: {exc}")
        try:
            dep = self.dependencies["libarchive-tools"]
            lib_dirs = ":".join(str(d) for d in dep.cpp_info.libdirs)
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={lib_dirs}:$LD_LIBRARY_PATH; "
                "./test_libarchive_api'",
                env="conanrun")
            passed += 1
        except Exception as exc:
            self.output.error(f"test_libarchive_api failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "bash test_bsdtar.sh && ./test_libarchive_api",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        ut_result = self._upstream_result()
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package functional tests failed")
        if ut_result["status"] != "passed":
            raise ConanException(
                "upstream make check did not fully pass "
                f"(passed={ut_result['passed']} failed={ut_result['failed']})")

    def _upstream_result(self):
        """Build the upstream marker from the stashed make check summary.

        The numbers come from the real `make check` automake summary captured
        during build(); nothing here is estimated.
        """
        dep = self.dependencies["libarchive-tools"]
        summary_path = os.path.join(
            dep.package_folder, "res", "libarchive-tools", "check-summary.json")
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except OSError as exc:
            return {
                "status": "failed",
                "framework": "autotools",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "reason": f"check-summary.json missing from package: {exc}",
            }
        total = int(summary.get("total", 0))
        failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
        passed = int(summary.get("passed", 0))
        skipped = int(summary.get("skipped", 0))
        check_ok = bool(summary.get("check_ok", False))
        parsed = bool(summary.get("parsed", False))
        if parsed and check_ok and failed == 0 and total > 0:
            return {
                "status": "passed",
                "framework": "autotools",
                "command": "make check",
                "discovered": total,
                "executed": total,
                "passed": passed,
                "failed": 0,
                "skipped": skipped,
            }
        return {
            "status": "failed",
            "framework": "autotools",
            "command": "make check",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": (
                "package res check-summary.json reports make check "
                f"total={total} passed={passed} failed={failed} "
                f"skipped={skipped} check_ok={check_ok}; see make-check.log"),
        }
