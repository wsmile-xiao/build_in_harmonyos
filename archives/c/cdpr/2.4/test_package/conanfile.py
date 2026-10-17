#!/usr/bin/env python3
"""Conan test_package — cdpr 2.4.

cdpr is a command-line packet tool, so the L1 test runs the real binary
(R34): `cdpr -h` exercises the startup banner, the getopt option parser
and the usage printer without touching the network (safe under CI —
a bare `cdpr` run would block up to 300s waiting for a CDP packet).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException


class CdprTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `cdpr -h` exits 0 and its output is non-empty
        #   2. output contains the product banner + Version 2.4
        #   3. output contains the usage text (device/usage markers)
        discovered = 3
        passed = 0
        try:
            self.run("%s test.sh" % bash, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as lzop/1.04, which passed the full gate).
        # test_package count = the 3 real smoke assertions in test.sh.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "%s test.sh" % bash,
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        # Upstream cdpr 2.4 has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the
        # Makefile defines only the `cdpr` and `clean` targets, so the
        # honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cdpr-2.4.tgz audited (sha256 "
                "32d3b58d8be7e2f78834469bd5f48546450ccc2a86d513177311cce994dfbec5): "
                "no tests/ directory and no test source files anywhere in the "
                "tree (no TEST(/TEST_F, no def test_); Makefile defines only "
                "the cdpr and clean targets with no check/test/TESTS targets, "
                "so make check has no rule to execute"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
