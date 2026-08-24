#!/usr/bin/env python3
"""Conan test_package — athena-jot 9.0.

验证 jot 可执行并实际运行（R34：实质调用被测包）。
调用 test_jot.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class AthenajotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["athena-jot"].package_folder,
            "usr", "local", "bin")
        script = os.path.join(self.source_folder, "test_jot.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
