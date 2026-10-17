#!/usr/bin/env python3
"""Conan test_package for intltool-debian — R34 real artifact verification.

L1 official test: runs a Python script that verifies the packaged Perl tools
(intltool-extract/intltool-merge/intltool-update) exist under <pkg>/bin/, are
executable, pass `perl -wc` syntax check, and that intltool-update actually
executes (via perl interpreter bridge) and reports 0.35.0. R34 real artifact
verification.
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
            pkg = self.dependencies["intltool-debian"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_intltool_debian.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
