#!/usr/bin/env python3
"""Conan test_package for gpgmepy 2.0.0 — 消费测试验证包安装布局。

用法: python3 test_gpgmepy.py <package_folder> <python_pkg_folder>
"""
import os

from conan import ConanFile


class GpgmepyTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("python/3.12.9")

    def test(self):
        # 按名索引取包目录（禁止迭代 self.dependencies：CI conan 版本
        # 对 int 迭代抛 TypeError: argument of type 'int' is not iterable）。
        pkg = self.dependencies["gpgmepy"].package_folder
        py_pkg = self.dependencies["python"].package_folder
        # gpgmepy 包内 site-packages: <pkg>/lib/python3.12/site-packages；
        # 解释器: <py pkg>/bin/python3.12（_gpgme*.so 由该解释器编译）。
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        self.run('python3 test_gpgmepy.py "%s" "%s"' % (site, py_bin),
                 env="conanrun")
