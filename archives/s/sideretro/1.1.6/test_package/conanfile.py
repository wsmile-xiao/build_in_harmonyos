#!/usr/bin/env python3
"""Conan test_package — sideretro 1.1.6.

验证 sider CLI 可执行并实际运行（R34：实质调用被测包）。
调用 test.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class SideretroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["sideretro"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun")