#!/usr/bin/env python3
"""Conan test_package for cfourcc — runs the R34 consumer check.

L1 official test: runs a Python script that executes the installed cfourcc
binary (`-h`) and asserts the version banner, proving it is runnable
(application package_type — no libs to link).
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
            pkg = self.dependencies["cfourcc"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_cfourcc.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
