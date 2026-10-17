#!/usr/bin/env python3
"""Conan test_package for dtach 0.9."""

import os
import sys

from conan import ConanFile


class DtachTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_dtach.py")
        binary = os.path.join(self.dependencies["dtach"].package_folder, "bin", "dtach")
        self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
