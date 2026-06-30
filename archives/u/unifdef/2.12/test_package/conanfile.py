#!/usr/bin/env python3
"""Conan test_package for unifdef 2.12.

unifdef is a terminal tool (binary), not a library.
This test verifies the binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class UnifdefTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["unifdef"].package_folder, "bin", "unifdef")
        self.run(f'"{bin_path}" -V')
