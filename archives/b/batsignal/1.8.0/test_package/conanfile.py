#!/usr/bin/env python3
"""Conan test_package for batsignal 1.8.0 — 消费测试验证可执行 + usage。

用法: python3 test_batsignal.py <package_folder>
"""
from conan import ConanFile


class BatsignalTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本 test_batsignal.py 与配方同目录（build_folder 即归档
        # test_package 目录）——直接运行，不做 copy（避免 test_package/
        # test_package/ 嵌套污染，airview 意见）
        pkg_folder = self.dependencies["batsignal"].package_folder
        self.run('python3 test_batsignal.py "%s"' % pkg_folder,
                 env="conanrun")
