#!/usr/bin/env python3
"""Conan test_package — randmac 0.2.

验证 randmac 可执行文件真实运行并断言行为（R34：实质使用被测包）。
调用 test_randmac.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class RandmacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["randmac"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_randmac.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
