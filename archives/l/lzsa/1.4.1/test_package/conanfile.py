#!/usr/bin/env python3
"""Conan test_package — lzsa 1.4.1

L1 test: verify the lzsa binary is installed and functional.
lzsa is a command-line tool (not a library), so we test the binary directly.
"""
import os

from conan import ConanFile


class LzsaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use full path to the binary (more reliable than relying on PATH)
        bin_path = os.path.join(self.dependencies["lzsa"].package_folder, "bin", "lzsa")
        if not os.path.isfile(bin_path):
            raise AssertionError(f"lzsa binary not found at {bin_path}")
        # L2 smoke test: --version must return exit code 0
        self.run(f'"{bin_path}" --version')
