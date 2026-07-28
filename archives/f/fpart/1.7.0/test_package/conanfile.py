#!/usr/bin/env python3
"""Conan test_package for fpart 1.7.0 — binary tool smoke test.

Verifies that the fpart binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class FpartTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["fpart"].package_folder, "bin", "fpart")
        self.run(f'"{bin_path}" --version', env="conanrun")
