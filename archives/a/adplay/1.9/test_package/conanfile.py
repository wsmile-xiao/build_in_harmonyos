#!/usr/bin/env python3
"""Conan test_package for adplay 1.9 — 验证 adplay 二进制可执行。

用法: python3 test_adplay.py <package_folder>
"""
from conan import ConanFile


class AdplayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（build_folder 即归档 test_package 目录）——
        # 直接运行，不做 copy（避免 test_package/test_package/ 嵌套污染）
        pkg_folder = self.dependencies["adplay"].package_folder
        self.run('python3 test_adplay.py "%s"' % pkg_folder, env="conanrun")
