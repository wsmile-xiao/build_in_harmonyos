#!/usr/bin/env python3
"""Conan test_package for strace 6.19 — binary tool smoke test.

Verifies that the strace binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class StraceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the strace binary in the package
        bin_path = os.path.join(self.dependencies["strace"].package_folder, "bin", "strace")
        if not os.path.exists(bin_path):
            # Try alternate path
            for root, dirs, files in os.walk(self.dependencies["strace"].package_folder):
                if "strace" in files:
                    bin_path = os.path.join(root, "strace")
                    break
        self.run(f'"{bin_path}" --version', env="conanrun")
