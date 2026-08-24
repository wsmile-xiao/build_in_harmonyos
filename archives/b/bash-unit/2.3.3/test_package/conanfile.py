#!/usr/bin/env python3
"""Conan test_package for bash-unit。"""
import os
import subprocess
import sys

from conan import ConanFile


class BashUnitTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_bash_unit.py")
        pkg = self.dependencies["bash-unit"].package_folder
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
