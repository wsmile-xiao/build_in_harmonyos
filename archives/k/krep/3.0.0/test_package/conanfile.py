#!/usr/bin/env python3
"""Conan test_package — krep 3.0.0"""
import os
from conan import ConanFile


class KrepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        krep_bin = os.path.join(self.dependencies["krep"].package_folder, "bin", "krep")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{krep_bin}" "{self.build_folder}"', env="conanrun")
