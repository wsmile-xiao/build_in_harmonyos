#!/usr/bin/env python3
"""Conan test_package — asciitex 0.21

Tests the installed asciiTeX binary by running it with -v flag.
"""
import os

from conan import ConanFile


class AsciitexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the binary path from the dependency package folder
        dep = self.dependencies["asciitex"]
        bin_path = os.path.join(dep.package_folder, "bin", "asciiTeX")
        self.output.info(f"Testing binary: {bin_path}")
        self.run(f'"{bin_path}" -v', env="conanrun")
