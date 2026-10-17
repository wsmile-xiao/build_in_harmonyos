#!/usr/bin/env python3
"""Conan test_package — c2050 0.3b (application package consumer test).

Delegates real verification to the standalone test source
test_c2050.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["c2050"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_c2050.py")
        # 实质校验（R34）：bin/c2050 存在/非空/可执行 + 空输入实跑 rc=0
        # + bin/ps2lexmark 存在/非空 + lib/pkgconfig/c2050.pc 存在
        # （L1e 可破坏物，毁掉 bin/ 后测试必须 FAIL）
        self.run("python3 %s %s" % (test_script, pkg_root))
