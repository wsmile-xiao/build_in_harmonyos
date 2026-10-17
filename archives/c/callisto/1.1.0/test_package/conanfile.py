#!/usr/bin/env python3
"""Conan test_package — callisto 1.1.0 (application package consumer test).

Delegates real verification to the standalone test source
test_callisto.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["callisto"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_callisto.py")
        # 实质校验（R34）：bin/callisto 存在/非空/可执行 + -V 实跑 rc=0
        # + bin/callisto-sunschedule 存在/非空 + lib/pkgconfig/callisto.pc
        # 存在（L1e 可破坏物，毁掉 bin/ 后测试必须 FAIL）
        self.run("python3 %s %s" % (test_script, pkg_root))
