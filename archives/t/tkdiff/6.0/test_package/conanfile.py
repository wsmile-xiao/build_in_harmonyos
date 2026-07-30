#!/usr/bin/env python3
"""Conan test_package for tkdiff 6.0."""
import os
import sys

from conan import ConanFile


class TkdiffTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["tkdiff"]
        test_script = os.path.join(self.recipe_folder, "test_smoke.py")
        self.run(f'"{sys.executable}" "{test_script}" "{dep.package_folder}"', env="conanrun")
