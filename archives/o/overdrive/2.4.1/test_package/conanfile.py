#!/usr/bin/env python3
"""Conan test_package for overdrive/2.4.1 (pure Bash CLI).

The test script executes the *installed* bin/overdrive binary, so it verifies
the packaged artefact rather than the source tree.
"""
import os
import sys

from conan import ConanFile


class OverdriveTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_overdrive.py")
        pkg = self.dependencies["overdrive"].package_folder
        cmd = f'"{sys.executable}" "{test_script}" "{pkg}"'
        self.run(cmd, env="conanrun")
