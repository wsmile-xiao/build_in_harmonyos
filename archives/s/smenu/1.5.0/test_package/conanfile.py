#!/usr/bin/env python3
"""Conan test_package — smenu 1.5.0 (CLI tool).

smenu is a terminal CLI selection/filtering tool, not a library.
The L1 test runs the binary with --version to verify it works.
"""
import os

from conan import ConanFile


class SmenuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["smenu"].package_folder, "bin", "smenu")
        self.run(f"{bin_path} --version", env="conanrun")
