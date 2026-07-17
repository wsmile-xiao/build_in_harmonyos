#!/usr/bin/env python3
"""Conan test_package — ascii 3.32

Tests the ascii binary by running 'ascii -v' to verify version output.
ascii is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class AsciiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["ascii"].cpp_info.bindirs[0]
        ascii_bin = os.path.join(bin_dir, "ascii")
        # Run ascii -v to verify the binary works (ascii uses -v not --version)
        self.run(f'"{ascii_bin}" -v', env="conanrun")
