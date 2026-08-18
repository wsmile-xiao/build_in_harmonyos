#!/usr/bin/env python3
"""Conan test_package — lzop 1.04.

lzop is a command-line tool, so the L1 test runs the real binary (R34):
- `lzop --version` reports a version
- a real compress → decompress round-trip on a data file, asserting the
  decompressed content is byte-identical to the original.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class LzopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `lzop --version` reports lzop
        #   2. `lzop -c` produces a non-empty compressed stream
        #   3. `lzop -dc` round-trip is byte-identical to the input (cmp)
        discovered = 3
        passed = 0
        try:
            self.run(f"{bash} test.sh", env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test.sh failed: {exc}")

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as analog/homebrew + astra + virtualpg, which passed
        # the full gate). test_package count = the 3 real smoke assertions.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": f"{bash} test.sh",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream lzop 1.04 has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): make check is
        # automake's default empty target, so the honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "lzop-1.04.tar.gz audited (sha256 "
                "7e72b62a8a60aff5200a047eea0773a8fb205caf7acbe1774d95147f305a2f41): "
                "no tests/ directory and no test source files anywhere in the "
                "tree (find -name '*test*' only hits autoconf generated "
                "scripts); Makefile.am defines only bin_PROGRAMS=src/lzop plus "
                "doc install targets, with no TESTS/check_PROGRAMS/check-local; "
                "configure.ac contains no AC_CONFIG_TESTDIR; `make -n check` "
                "expands to automake's default empty target (check-am: all-am), "
                "so make check executes zero test cases"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
