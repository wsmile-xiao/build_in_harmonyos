#!/usr/bin/env python3
"""Conan test_package for cdw 0.8.1 — 失败记录归档完整性验证。

用法: python3 test_cdw.py <package_folder>
"""
from conan import ConanFile


class CdwTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cdw"].package_folder
        self.run('python3 test_cdw.py "%s"' % pkg_folder, env="conanrun")
