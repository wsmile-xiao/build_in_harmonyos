#!/usr/bin/env python3
"""Conan test_package for buildessential。"""
import os
import subprocess
import sys

from conan import ConanFile


class BuildessentialTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_buildessential.py")
        pkg = self.dependencies["buildessential"].package_folder
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
