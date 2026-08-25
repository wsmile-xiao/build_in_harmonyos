#!/usr/bin/env python3
"""Conan test_package for cadaver 0.24.0 — binary invocation test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class CadaverTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            bin_dir = os.path.join(
                self.dependencies["cadaver"].package_folder, "bin")
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_cadaver.py")
            self.run(f'{python_exe} "{test_script}" "{bin_dir}"',
                     env="conanrun")
