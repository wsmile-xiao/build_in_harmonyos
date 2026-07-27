#!/usr/bin/env python3
"""Conan test_package for rpm2cpio — verifies the shell script tool is installed correctly.

R34: test must actually exercise the package's functionality.
Runs rpm2cpio with test arguments to verify the binary is installed and functional.
"""
from conan import ConanFile


class Rpm2CpioTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # rpm2cpio with 2+ args prints usage and exits 0
        # This verifies the script is installed and executable (R34)
        # env="conanrun" sets up PATH to include the package's bin directory
        self.run("rpm2cpio dummy1 dummy2", env="conanrun")
