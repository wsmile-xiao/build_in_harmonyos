#!/usr/bin/env python3
"""Conan test_package for lfortran 0.64.0 — consumer check.

Runs test_lfortran.py (standalone test driver, satisfies L0c) via self.run
with env="conanrun"（conanrun 环境注入 clang/22.1.8 传递依赖的 LD_LIBRARY_PATH，
裸 subprocess 会丢失 libLLVM.so 路径 —— sdcc/yarl 同款教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class LFortranTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lfortran"].package_folder
        bindir = os.path.join(pkg, "bin")
        if not os.path.isfile(os.path.join(bindir, "lfortran")):
            raise ConanException("lfortran binary missing under {}".format(bindir))
        test_script = os.path.join(os.path.dirname(__file__), "test_lfortran.py")
        if not os.path.isfile(test_script):
            raise ConanException("test_lfortran.py missing: {}".format(test_script))
        # test_lfortran.py 期望 <package-folder>（内部拼 bin/lfortran + include 头路径）
        self.run("python3 '{}' '{}'".format(test_script, pkg), env="conanrun")
