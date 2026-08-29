#!/usr/bin/env python3
"""Conan test_package for calceph 5.0.0 — 消费测试验证库安装布局。

用法: python3 test_calceph.py <package_folder>
"""
from conan import ConanFile


class CalcephTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["calceph"].package_folder
        self.run('python3 test_calceph.py "%s"' % pkg_folder, env="conanrun")
