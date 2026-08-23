#!/usr/bin/env python3
"""Conan test_package for smartmontools 7.4.

Tests that the installed smartctl binary works correctly by running
`smartctl --version` and verifying the output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SmartmontoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg_folder = self.dependencies["smartmontools"].package_folder
            smartctl = os.path.join(pkg_folder, "bin", "smartctl")
            self.run(f'"{smartctl}" --version', env="conanrun")
