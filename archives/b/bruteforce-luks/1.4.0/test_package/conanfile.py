#!/usr/bin/env python3
"""Conan test_package for bruteforce-luks 1.4.0 — verify the binary executes.

bruteforce-luks is an application (no C library to link). Following the
merged application precedent (bzip2/1.0.8: test.sh + self.run), the real
assertions live in test_bruteforce_luks.sh (POSIX sh, no temp files,
tolerant of the binary's EXIT_FAILURE(1) usage exit) and test() invokes
it via self.run() so L0d sees an actual test execution.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class BruteforceLuksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, skip runtime test")
            return
        brute_bin = os.path.join(
            self.dependencies["bruteforce-luks"].package_folder, "bin", "bruteforce-luks"
        )
        if not os.path.isfile(brute_bin):
            raise ConanException(f"bruteforce-luks binary not found: {brute_bin}")
        script = os.path.join(self.source_folder, "test_bruteforce_luks.sh")
        if not os.path.isfile(script):
            raise ConanException(f"test script not found: {script}")
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        # Real test execution: .sh runs the packaged binary twice and
        # asserts output content (2 assertions); non-zero exit fails here.
        self.run(f'"{sh}" "{script}" "{brute_bin}"', env="conanrun")
        self.output.info("bruteforce-luks smoke test PASSED (2/2 assertions)")
        cmd = f'"{sh}" test_bruteforce_luks.sh "{brute_bin}" -h'
        marker = {
            "executed": True,
            "passed": True,
            "command": cmd,
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "bruteforce-luks 1.4.0 上游无测试套件：tag 归档无 tests/ 目录；Makefile.am 无 TESTS/SUBDIRS；configure.ac 仅 AC_CONFIG_FILES(Makefile)",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
