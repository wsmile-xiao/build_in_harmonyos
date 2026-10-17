#!/usr/bin/env python3
"""Test package for wpa_supplicant 2.11.

Runs wpa_supplicant --version to verify the binary is functional.
"""
import os

from conan import ConanFile


class WpaSupplicantTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Use full path to the binary from the package
        bin_dir = self.dependencies["wpa_supplicant"].cpp_info.bindirs[0]
        bin_path = os.path.join(bin_dir, "wpa_supplicant")
        self.run(f'"{bin_path}" --version', env="conanrun")
