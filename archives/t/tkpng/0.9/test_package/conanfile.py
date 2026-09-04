#!/usr/bin/env python3
"""Conan test_package for tkpng — runs the R34 consumer check.

L1 official test: runs a script that loads the packaged tkpng0.9.so via
tclsh and does `package require tkpng`, verifying the PNG format is
registered. R34 real API usage, not just file presence.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["tkpng"].package_folder
            # tkpng 依赖 tk/9.0.3.2（自动带 tcl/9.0.3.2）——test 需 tcl 包的 tclsh9.0
            tcl_pkg = None
            try:
                tcl_pkg = self.dependencies["tcl"].package_folder
            except Exception:
                pass
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_tkpng.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}" "{tcl_pkg or ""}"',
                     env="conanrun")
