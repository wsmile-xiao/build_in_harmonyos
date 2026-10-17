#!/usr/bin/env python3
"""Conan test_package — munin-c 0.0.13.

验证包内程序真实可执行并断言行为（R34）：
调用 test_munin_c.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class MuninCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        sbin_dir = os.path.join(self.dependencies["munin-c"].package_folder, "sbin")
        script = os.path.join(self.source_folder, "test_munin_c.sh")
        self.run(f'sh "{script}" "{sbin_dir}"')
