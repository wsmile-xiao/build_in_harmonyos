#!/usr/bin/env python3
"""Conan test_package — flawfinder 2.0.10.

验证 flawfinder 可执行并实际扫描含漏洞样本（R34：实质调用被测包）。
调用 test_flawfinder.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class FlawfinderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["flawfinder"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_flawfinder.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
