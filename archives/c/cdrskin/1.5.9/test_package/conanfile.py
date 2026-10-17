#!/usr/bin/env python3
"""Conan test_package for cdrskin 1.5.9 — 消费测试验证 CLI 工具。

用法: python3 test_cdrskin.py <package_folder>
"""
from conan import ConanFile


class CdrskinTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdrskin"].package_folder
        self.run('python3 test_cdrskin.py "%s"' % pkg_folder, env="conanrun")
