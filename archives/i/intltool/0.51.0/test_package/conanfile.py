#!/usr/bin/env python3
"""Conan test_package for intltool — runs the R34 consumer check.

L1 official test: runs a Python script that verifies the packaged Perl tools
(intltool-update/intltoolize/intltool-extract) exist under <pkg>/bin/ and that
intltool-update --version actually executes and reports 0.51.0. R34 real
artifact verification.
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
            pkg = self.dependencies["intltool"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_intltool.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
