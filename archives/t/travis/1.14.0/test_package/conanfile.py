#!/usr/bin/env python3
"""Conan test_package for travis 1.14.0."""
import os

from conan import ConanFile


class TravisTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["travis"].package_folder
        test_script = os.path.join(self.recipe_folder, "test_travis.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
        upstream_script = os.path.join(self.recipe_folder, "run_upstream_tests.sh")
        self.run(f'sh "{upstream_script}" "{pkg_folder}"', env="conanrun")
