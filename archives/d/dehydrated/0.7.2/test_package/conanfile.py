#!/usr/bin/env python3
"""Conan test_package — dehydrated 0.7.2 (pure Bash ACME client consumer test).

Delegates real verification to the standalone test source
test_dehydrated.py (invoked via self.run(), satisfying L0c/L0d:
test_package contains a non-conanfile.py test source).
"""
import os

from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["dehydrated"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_dehydrated.py")
        # 实质校验（R34）：bin/dehydrated 存在 + bash -n 语法自检 +
        # --version 冒烟（真实执行脚本内置依赖检查并核对版本输出）
        self.run("python3 %s %s" % (test_script, pkg_root))
