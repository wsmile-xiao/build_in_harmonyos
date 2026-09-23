#!/usr/bin/env python3
"""Conan test_package for cream 0.43."""
import os
import sys

from conan import ConanFile


class CreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["cream"]
        cream_dir = os.path.join(str(dep.package_folder), "share", "vim", "cream")
        test_script = os.path.join(self.recipe_folder, "test_smoke.py")
        self.run(f'"{sys.executable}" "{test_script}" "{cream_dir}"', env="conanrun")
