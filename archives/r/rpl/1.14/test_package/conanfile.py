#!/usr/bin/env python3
"""Conan test_package — rpl 1.14.

验证 rpl 可执行并完成实际文本替换（R34：实质调用被测包二进制）。
调用 test_rpl.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class RplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["rpl"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_rpl.sh")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun")
