#!/usr/bin/env python3
"""Conan test_package — bashacks 1.5-git20260330.988ab7e.

验证 bashacks.sh 函数库可 source 并调用 bh_* 函数（R34：实质调用被测包）。
调用 test_bashacks.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class BashacksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        lib_dir = os.path.join(
            self.dependencies["bashacks"].package_folder,
            "share", "bashacks")
        script = os.path.join(self.source_folder, "test_bashacks.sh")
        self.run(f'sh "{script}" "{lib_dir}"')
