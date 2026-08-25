#!/usr/bin/env python3
"""Conan test_package for bsdmainutils 12.1.8 — 消费测试验证 calendar/ncal。

用法: python3 test_bsdmainutils.py <package_folder>
"""
from conan import ConanFile


class BsdmainutilsTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本 test_bsdmainutils.py 与配方同目录（build_folder 即归档
        # test_package 目录）——直接运行，不做 copy（避免 test_package/
        # test_package/ 嵌套污染，airview 意见）
        pkg_folder = self.dependencies["bsdmainutils"].package_folder
        self.run('python3 test_bsdmainutils.py "%s"' % pkg_folder,
                 env="conanrun")
