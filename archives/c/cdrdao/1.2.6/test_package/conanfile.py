#!/usr/bin/env python3
"""Conan test_package for cdrdao 1.2.6 — 消费测试验证 CLI 工具。

用法: python3 test_cdrdao.py <package_folder>
"""
from conan import ConanFile


class CdrdaoTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdrdao"].package_folder
        self.run('python3 test_cdrdao.py "%s"' % pkg_folder, env="conanrun")
