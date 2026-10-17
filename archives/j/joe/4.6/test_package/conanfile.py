#!/usr/bin/env python3
"""Conan test_package for joe 4.6 — binary tool smoke test.

Verifies that the joe binary is installed and runs correctly.
joe does not support --version, but --help outputs version info.
"""
import os

from conan import ConanFile


class JoeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the joe binary in the package
        bin_path = os.path.join(self.dependencies["joe"].package_folder, "bin", "joe")
        if not os.path.exists(bin_path):
            for root, dirs, files in os.walk(self.dependencies["joe"].package_folder):
                if "joe" in files:
                    bin_path = os.path.join(root, "joe")
                    break
        if not os.path.exists(bin_path):
            raise Exception(f"joe binary not found in package: {self.dependencies['joe'].package_folder}")
        # joe --help outputs version info on first line
        self.run(f'"{bin_path}" --help', env="conanrun")
