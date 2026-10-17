#!/usr/bin/env python3
"""Conan test_package — aircrack 1.7 (CLI tool suite)."""

import json

from conan import ConanFile
from conan.tools.build import can_run


class AircrackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        discovered = 2
        passed = 0
        try:
            # 二进制可运行性验证
            self.run("aircrack-ng --help > /dev/null 2>&1", env="conanrun")
            passed += 1
        except Exception:
            pass
        try:
            # 真实功能验证：WPA2 握手包破解（复用上游 test-aircrack-ng-0001.sh 用例）
            self.run("sh test.sh", env="conanrun")
            passed += 1
        except Exception:
            pass
        marker = {
            "executed": True,
            "passed": passed == discovered,
            "command": "aircrack-ng --help; sh test.sh",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if passed != discovered:
            raise Exception("test_package checks failed: %d/%d" % (passed, discovered))
