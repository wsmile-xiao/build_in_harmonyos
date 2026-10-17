#!/usr/bin/env python3
"""Conan test package for the stm32flash command-line interface."""
import os
import sys

from conan import ConanFile


class Stm32flashTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["stm32flash"].package_folder
        binary = os.path.join(package, "bin", "stm32flash")
        script = os.path.join(self.source_folder, "test_cli.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
