#!/usr/bin/env python3
"""Conan test_package — inxi 3.3.38-1.

验证 inxi 可执行并完成实际系统信息查询（R34：实质调用被测包）。
调用 test_inxi.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class InxiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["inxi"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_inxi.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
