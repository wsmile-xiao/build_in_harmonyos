#!/usr/bin/env python3
"""Conan test_package — cdrom-detect 1.115 (script package consumer test).

Delegates real verification to the standalone test source
test_cdrom_detect.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["cdrom-detect"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_cdrom_detect.py")
        # 实质校验（R34）：lib/finish-install.d/15cdrom-detect 存在、非空、
        # 可执行、sh -n 解析通过；lib/pkgconfig/cdrom-detect.pc 存在
        # （L1e 可破坏物，毁掉 lib/ 后测试必须 FAIL）
        self.run("python3 %s %s" % (test_script, pkg_root))
