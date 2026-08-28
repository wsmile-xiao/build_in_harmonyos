#!/usr/bin/env python3
"""Conan test_package for cdrecord 2024-03-21 — 消费测试验证 CLI 工具。

用法: python3 test_cdrecord.py <package_folder>
"""
from conan import ConanFile


class CdrecordTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdrecord"].package_folder
        self.run('python3 test_cdrecord.py "%s"' % pkg_folder, env="conanrun")
