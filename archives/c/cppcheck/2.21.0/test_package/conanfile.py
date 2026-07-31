#!/usr/bin/env python3
"""Conan test_package — cppcheck 2.21.0"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class CppcheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.dependencies["cppcheck"].package_folder,
                                    "bin", "cppcheck")
            test_file = os.path.join(self.source_folder, "test.c")
            # 验证 cppcheck 可执行文件可用
            self.run(f"{bin_path} --version", env="conanrun")
            # 对测试文件运行静态分析，验证实际功能
            self.run(f"{bin_path} --enable=all --suppress=missingIncludeSystem {test_file}",
                     env="conanrun")
