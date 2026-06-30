#!/usr/bin/env python3
"""Conan test_package — dex 1.0.

dex is a terminal text editor (executable), not a library.
This test verifies the binary is installed and is a valid ELF executable.
"""
import os

from conan import ConanFile


class DexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # dex is a full-screen text editor requiring a terminal.
        # We verify the binary exists and is a valid ELF executable.
        pkg_folder = self.dependencies["dex"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "dex")
        if not os.path.isfile(bin_path):
            # Search recursively for the binary
            for root, dirs, files in os.walk(pkg_folder):
                if "dex" in files:
                    bin_path = os.path.join(root, "dex")
                    break
        assert os.path.isfile(bin_path), f"dex binary not found in package"
        # Verify it's a valid ELF file
        with open(bin_path, "rb") as f:
            magic = f.read(4)
            assert magic == b'\x7fELF', f"dex is not a valid ELF binary (got {magic})"
        print(f"test dex 1.0: OK (binary at {bin_path})")
