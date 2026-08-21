#!/usr/bin/env python3
"""Conan test_package — autotalent 0.2.

验证 autotalent.so LADSPA 插件编译产物存在且含 LADSPA 描述符号
（R34：实质检查被测包产物）。调用 test_autotalent.sh 测试脚本。
"""
import os

from conan import ConanFile


class AutotalentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_dir = os.path.join(
            self.dependencies["autotalent"].package_folder, "ladspa")
        script = os.path.join(self.source_folder, "test_autotalent.sh")
        self.run(f'sh "{script}" "{pkg_dir}"')
