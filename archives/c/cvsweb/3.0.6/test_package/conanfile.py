#!/usr/bin/env python3
"""Conan test_package — cvsweb 3.0.6 (pure Perl CGI consumer test).

Delegates real verification to the standalone test source
test_cvsweb.py (invoked via self.run(), satisfying L0c/L0d:
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
        pkg = self.dependencies["cvsweb"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_cvsweb.py")
        # 实质校验（R34）：cvsweb.cgi 存在 + perl -T -c 语法自检（PERL5LIB/-I
        # 指向捆绑模块，taint 模式下 PERL5LIB 被 perl 忽略须用 -I）
        self.run("python3 %s %s" % (test_script, pkg_root))
