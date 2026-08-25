#!/usr/bin/env python3
"""Conan test_package for esniper 2.35.0.

R34: test substantively exercises the package — runs test.sh which
executes esniper --version and validates the output.
"""
import os

from conan import ConanFile


class EsniperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run test.sh which executes esniper --version and validates output
        bin_dir = os.path.join(self.dependencies["esniper"].package_folder, "bin")  # esniper
        esniper_bin = os.path.join(bin_dir, "esniper")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{test_script}" "{esniper_bin}"', env="conanrun")
