#!/usr/bin/env python3
"""Conan test_package for cdda2wav 2024-03-21 — 消费测试验证 CLI 工具。

用法: python3 test_cdda2wav.py <package_folder>
"""
from conan import ConanFile


class Cdda2wavTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdda2wav"].package_folder
        self.run('python3 test_cdda2wav.py "%s"' % pkg_folder, env="conanrun")
