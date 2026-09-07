#!/usr/bin/env python3
"""Conan test_package for ccbuild 2.0.11 — 消费测试验证 CLI 工具。

用法: python3 test_ccbuild.py <package_folder>
"""
from conan import ConanFile


class CcbuildTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（build_folder 即归档 test_package 目录）——
        # 直接运行，不做 copy（避免 test_package/test_package/ 嵌套污染）
        pkg_folder = self.dependencies["ccbuild"].package_folder
        self.run('python3 test_ccbuild.py "%s"' % pkg_folder, env="conanrun")
