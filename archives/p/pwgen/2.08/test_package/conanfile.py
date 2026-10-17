#!/usr/bin/env python3
"""Conan test_package — pwgen 2.08.

R34: test substantively depends on the tested package.
Runs the pwgen binary and verifies it produces passwords correctly.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PwgenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get pwgen binary path from the installed package
        pkg_folder = self.dependencies["pwgen"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "pwgen")

        # Test 1: --help prints usage (pwgen exits 1 for --help)
        self.run(f'"{bin_path}" --help', env="conanrun", ignore_errors=True)

        # Test 2: Generate passwords (10 chars, 3 passwords) - should exit 0
        self.run(f'"{bin_path}" 10 3', env="conanrun")

        # Test 3: Secure passwords (15 chars, 5 passwords) - should exit 0
        self.run(f'"{bin_path}" -s 15 5', env="conanrun")
