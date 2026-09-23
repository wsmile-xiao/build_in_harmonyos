#!/usr/bin/env python3
"""Conan test_package — cdrom-checker 1.69 (C application consumer test).

Delegates real verification to the standalone test source
test_cdrom_checker.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["cdrom-checker"]
        pkg_root = pkg.package_folder
        cdebconf_root = self.dependencies["cdebconf"].package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_cdrom_checker.py")
        # 实质校验（R34）：bin/cdrom-checker 存在、非空、可执行、是 ELF、
        # DT_NEEDED 真实引用 libdebconfclient.so.0 与 libdebian-installer.so.4
        # （验证构建时链接依赖真实解析，而非静态假产物）+ 以 MENU +
        # DEBCONF passthrough 前端 + 可写 textdb 真实执行一次（断言 rc=0
        # 与 debconf set/input/go/get 交互输出），区分源码构建产物与
        # 手工塞入的预编译二进制
        self.run("python3 %s %s %s" % (test_script, pkg_root, cdebconf_root))
