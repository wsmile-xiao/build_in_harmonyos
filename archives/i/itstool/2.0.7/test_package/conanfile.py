#!/usr/bin/env python3
"""Conan test_package — itstool 2.0.6.

验证 itstool 可执行并实际运行（R34：实质调用被测包）。
调用 test_itstool.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class ItstoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["itstool"].package_folder,
            "usr", "local", "bin")
        script = os.path.join(self.source_folder, "test_itstool.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
