#!/usr/bin/env python3
"""Conan test_package — ai.robots.txt 1.47 (data package consumer test).

Delegates real verification to the standalone test source
test_ai_robots_txt.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["ai.robots.txt"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_ai_robots_txt.py")
        # 实质校验（R34）：robots.txt 存在且含 User-agent: 块、
        # lib/pkgconfig/*.pc 存在（L1e 可破坏物，毁掉 lib/ 后测试必须 FAIL）
        self.run("python3 %s %s" % (test_script, pkg_root))
