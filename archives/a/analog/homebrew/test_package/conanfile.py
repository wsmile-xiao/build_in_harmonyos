#!/usr/bin/env python3
"""Conan test_package — analog homebrew (upstream 6.0.18)

L1 test: verify the analog binary is installed and can process a log file.
Also emits HMBS evidence markers for the machine verification gate.
"""

import json
import os
from conan import ConanFile
from conan.tools.build import can_run


class AnalogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["analog"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "analog")
        sample_log = os.path.join(pkg_folder, "res", "analog", "examples", "logfile.log")

        test_package_passed = True
        if can_run(self):
            # Test 1: --help works
            self.run(f'"{bin_path}" --help', env="conanrun")

            # Test 2: --version works
            self.run(f'"{bin_path}" --version', env="conanrun")

            # Test 3: Process sample log file (if available)
            if os.path.isfile(sample_log):
                self.run(f'"{bin_path}" +g"{sample_log}"', env="conanrun")
            else:
                self.output.info("Sample log not found, skipping log processing test")
        else:
            self.output.info("Cross-compiling, skipping runtime tests")
            test_package_passed = False

        # Emit HMBS machine evidence markers
        # HMBS_TEST_PACKAGE_RESULT — test_package verification
        tp_result = {
            "executed": can_run(self),
            "passed": test_package_passed,
            "command": f'"{bin_path}" --help && "{bin_path}" --version',
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # HMBS_UPSTREAM_TEST_RESULT — upstream test suite audit
        # analog-ce 6.0.18 has no upstream test suite (no test/, no CTest, no make check)
        ut_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "审计 upstream analog-ce 6.0.18: 源码目录无 test/ 或 tests/ 文件夹；"
                "无 CMakeLists.txt 的 enable_testing/add_test；"
                "无 Makefile 的 check/test 目标；"
                "无 configure --enable-tests 选项；"
                "发布包不含任何测试框架或测试套件。"
                "analog 是一个纯命令行日志分析工具，上游仅提供 README 中的手动使用示例。"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")