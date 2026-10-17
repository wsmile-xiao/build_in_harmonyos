#!/usr/bin/env python3
"""Conan test_package for tomli-w — runs the R34 consumer check.

L1 official test: runs a Python script that imports the packaged tomli_w
and dumps a dict to a TOML string. R34 real API usage, not just presence.
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
            pkg = self.dependencies["tomli-w"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_tomli_w.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
