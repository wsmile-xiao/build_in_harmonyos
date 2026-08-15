#!/usr/bin/env python3
"""Conan test_package — tofrodos 1.8.3.

验证 fromdos/todos 可执行并完成实际 DOS→Unix 换行转换（R34：实质调用）。
调用 test_fromdos.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class TofrodosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["tofrodos"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_fromdos.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
