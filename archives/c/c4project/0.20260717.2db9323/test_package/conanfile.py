#!/usr/bin/env python3
"""Conan test_package for c4project 1.0.0 — 消费测试验证 CMake 模块集。

用法: python3 test_c4project.py <package_folder>
"""
from conan import ConanFile


class C4projectTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（build_folder 即归档 test_package 目录）——
        # 直接运行，不做 copy（避免 test_package/test_package/ 嵌套污染）
        pkg_folder = self.dependencies["c4project"].package_folder
        self.run('python3 test_c4project.py "%s"' % pkg_folder, env="conanrun")
