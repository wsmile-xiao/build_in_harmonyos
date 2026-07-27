#!/usr/bin/env python3
"""Conan test_package — apg 2.2.3

L1 test: verify the apg binary is installed and can generate passwords.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ApgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the apg binary in the package folder
        pkg_folder = self.dependencies["apg"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "apg")
        if can_run(self):
            # R34: Test must actually exercise the packaged binary
            self.run(f'"{bin_path}" -v', env="conanrun")
            self.run(f'"{bin_path}" -n 5 -m 8 -x 10', env="conanrun")
