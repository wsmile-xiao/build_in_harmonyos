#!/usr/bin/env python3
"""Conan test_package — rolldice 1.16

Tests the installed rolldice binary by running it with a simple dice expression.
"""
import os

from conan import ConanFile


class RolldiceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the installed binary with a simple dice expression
        bin_path = os.path.join(self.dependencies["rolldice"].package_folder, "bin", "rolldice")
        self.run(f"{bin_path} 1d6", env="conanrun")
