#!/usr/bin/env python3
"""Conan test_package — gpp 2.28

Tests the gpp binary by running 'gpp --version' and a simple
preprocessing test to verify the binary is functional.
gpp is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class GppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["gpp"].cpp_info.bindirs[0]
        gpp_bin = os.path.join(bin_dir, "gpp")
        # R34: Test must actually use the binary (not just print a string)
        # Run gpp --version to verify the binary works
        self.run(f'"{gpp_bin}" --version', env="conanrun")
        # Run a simple preprocessing test: define and expand a macro
        self.run(
            f'echo "#define FOO bar\\nFOO" | "{gpp_bin}"',
            env="conanrun"
        )
