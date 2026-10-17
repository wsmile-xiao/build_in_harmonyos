#!/usr/bin/env python3
"""Conan test_package for pipes-sh."""
import os
import sys

from conan import ConanFile


class PipesShTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_pipes_sh.py")
        pkg = self.dependencies["pipes-sh"].package_folder
        cmd = f'"{sys.executable}" "{test_script}" "{pkg}"'
        if os.name == "nt":
            self.run(cmd)
        else:
            self.run(cmd, env="conanrun")
