#!/usr/bin/env python3
"""Conan test_package — nettoe 1.5.1

nettoe is a terminal binary (not a library). This test verifies
that the binary is installed and can be executed.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class NettoeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy the nettoe binary from the package to the test build folder
        bin_dir = os.path.join(self.dependencies["nettoe"].package_folder, "bin")
        copy(self, "nettoe", bin_dir, self.build_folder)

    def test(self):
        # Verify the binary exists and is executable
        binary = os.path.join(self.build_folder, "nettoe")
        assert os.path.isfile(binary), f"nettoe binary not found at {binary}"
        self.run(f"{binary} --version", env="conanrun")
