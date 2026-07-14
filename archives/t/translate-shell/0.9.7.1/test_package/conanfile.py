#!/usr/bin/env python3
"""Test package for translate-shell 0.9.7.1.

Verifies that the `trans` binary is installed and can report its version.
"""
import os

from conan import ConanFile


class TranslateShellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["translate-shell"].package_folder
        trans_bin = os.path.join(pkg_folder, "bin", "trans")
        test_script = os.path.join(self.recipe_folder, "test_trans.sh")
        self.run(f'sh "{test_script}" "{trans_bin}"', env="conanrun")
