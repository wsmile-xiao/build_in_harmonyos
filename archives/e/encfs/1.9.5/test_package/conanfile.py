#!/usr/bin/env python3
"""Conan test_package for encfs 1.9.5 — 消费测试验证 CLI 工具。

用法: python3 test_encfs.py <package_folder>
"""
from conan import ConanFile


class EncfsTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["encfs"].package_folder
        self.run('python3 test_encfs.py "%s"' % pkg_folder, env="conanrun")
