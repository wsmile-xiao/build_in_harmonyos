#!/usr/bin/env python3
"""Conan test_package — dumb-init 1.2.5

R34: test must substantively depend on the tested package.
This test runs the actual dumb-init binary and verifies --version output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DumbInitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["dumb-init"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "dumb-init")
        if can_run(self):
            self.run(f'bash test_dumb_init.sh "{bin_path}"', env="conanrun")
