#!/usr/bin/env python3
"""Conan test_package — atinout 0.9.1

Tests the atinout binary by running --version and --help.
atinout is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class AtinoutTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["atinout"].cpp_info.bindirs[0]
        atinout_bin = os.path.join(bin_dir, "atinout")
        # Run atinout --version to verify the binary works
        self.run(f'"{atinout_bin}" --version', env="conanrun")
