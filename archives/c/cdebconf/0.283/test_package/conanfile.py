#!/usr/bin/env python3
"""Conan test_package for cdebconf 0.283 — 消费测试验证 CLI 工具。

用法: python3 test_cdebconf.py <package_folder>
"""
from conan import ConanFile


class CdebconfTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdebconf"].package_folder
        self.run('python3 test_cdebconf.py "%s"' % pkg_folder,
                 env="conanrun")
