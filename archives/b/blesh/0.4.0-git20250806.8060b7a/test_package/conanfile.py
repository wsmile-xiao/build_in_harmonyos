#!/usr/bin/env python3
"""Conan test_package for blesh。"""
import os
import sys

from conan import ConanFile


class BleshTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_blesh.py")
        pkg = self.dependencies["blesh"].package_folder
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
