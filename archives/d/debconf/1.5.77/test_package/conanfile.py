#!/usr/bin/env python3
"""Conan test_package for debconf — runs the R34 consumer check.

L1 official test: runs a Python script that (1) loads the packaged
Debconf::Config module via perl -I<lib>, (2) runs the packaged
debconf-escape CLI helper. R34 real API usage, not just file presence.
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
            pkg = self.dependencies["debconf"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_debconf.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
