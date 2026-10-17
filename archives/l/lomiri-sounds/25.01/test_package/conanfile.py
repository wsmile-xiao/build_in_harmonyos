#!/usr/bin/env python3
"""Consumer test for the Lomiri sound resource package."""

import os
import sys

from conan import ConanFile


class LomiriSoundsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["lomiri-sounds"].package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_resources.py")
        self.run(f'"{sys.executable}" "{test_script}" "{package_folder}"')
