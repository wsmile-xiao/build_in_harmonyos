#!/usr/bin/env python3
"""Consumer validation for the architecture-independent iso-codes package."""

import os
import sys

from conan import ConanFile


class IsoCodesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["iso-codes"].package_folder
        script = os.path.join(self.recipe_folder, "test_verify.py")
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, package_folder)
        )
