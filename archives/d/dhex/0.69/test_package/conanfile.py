#!/usr/bin/env python3
"""Conan test_package — dhex 0.69.

dhex is a command-line tool, so the L1 test runs the real binary (R34)
with its non-interactive flags (all exit before ncurses UI startup):
- `dhex -v` prints exactly "0.69"
- `dhex -h` prints the help screen containing DHEX
- `dhex -g` prints the GPL license text
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class DhexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        # The absolute HNP path is missing on some preflight workers,
        # so resolve via PATH before falling back to the hard-coded path.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `dhex -v` prints exactly "0.69"
        #   2. `dhex -h` help screen contains DHEX and is non-empty
        #   3. `dhex -g` license text contains GPL and is non-empty
        discovered = 3
        passed = 0
        try:
            self.run("{bash} test.sh".format(bash=bash), env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: {}".format(exc))

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as lzop 1.04, which passed the full gate).
        # test_package count = the 3 real binary assertions.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "{bash} test.sh".format(bash=bash),
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result)))

        # Upstream dhex 0.69 has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the
        # hand-written Makefile defines no check/test target, so the
        # honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "makefile",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "dhex_0.69.tar.gz audited (sha256 "
                "52730bcd1cf16bd4dae0de42531be9a4057535ec61ca38c0804eb8246ea6c41b): "
                "no tests/ directory and no test source files anywhere in the "
                "tree; the hand-written Makefile defines only all/dhex/install/clean "
                "targets with no check/test target; todo.txt admits the test suite "
                "is missing (\"write a test suite which checks if "
                "searching/correlation etc. works\"); mkrelease.sh only runs "
                "./dhex -v as a smoke check, so make check executes zero test cases"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result)))

        if passed != discovered:
            raise ConanException("test_package binary tests failed")
