#!/usr/bin/env python3
"""Consumer validation for the debian-ports-archive data package."""

import os
import sys

from conan import ConanFile


class DebianPortsArchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["debian-ports-archive"].package_folder
        script = os.path.join(self.recipe_folder, "test_verify.py")
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, package_folder)
        )