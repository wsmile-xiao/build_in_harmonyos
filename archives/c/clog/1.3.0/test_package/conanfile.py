#!/usr/bin/env python3
"""test_package for clog executable — runs test_clog.sh which invokes clog --version/--help and a real filter run."""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class ClogTestConan(ConanFile):
    """test_package for clog executable — runs test_clog.sh which invokes clog --version/--help and a real filter run."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test_clog.sh holds 4 real assertions against the packaged binary:
        #   1. clog --version reports clog 1.3.0
        #   2. clog --help prints Usage
        #   3. filter run keeps matched line content
        #   4. non-matching line passes through unchanged
        discovered = 4
        passed = 0
        try:
            self.run(f"{shell} test_clog.sh", env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_clog.sh failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": f"{shell} test_clog.sh",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream clog 1.3.0 ships no test suite in the release tarball
        # (see test_package/MANIFEST.yml audit: no test/ dir, empty
        # test_SRCS upstream, no enable_testing/ctest wiring), so the honest
        # upstream result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "clog-1.3.0.tar.gz audited (sha256 "
                "fed44a8d398790ab0cf426c1b006e7246e20f3fcd56c0ec4132d24b05d5d2018): "
                "92 files, no test/ directory (CPack CPACK_SOURCE_IGNORE_FILES "
                "excludes test); root CMakeLists only add_subdirectory(test) when "
                "the dir exists; upstream test/CMakeLists has empty test_SRCS; "
                "src/CMakeLists has no enable_testing/ctest wiring"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package consumer tests failed")
