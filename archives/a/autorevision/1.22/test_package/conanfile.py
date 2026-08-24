#!/usr/bin/env python3
"""Conan test_package — autorevision 1.22.

验证 autorevision 可执行并实际运行（R34：实质调用被测包）。
调用 test_autorevision.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class AutorevisionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["autorevision"]
        bin_dir = os.path.join(pkg.package_folder, "usr", "local", "bin")
        if not os.path.exists(os.path.join(bin_dir, "autorevision")):
            bin_dir = os.path.join(pkg.package_folder, "usr", "bin")
        script = os.path.join(self.source_folder, "test_autorevision.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
