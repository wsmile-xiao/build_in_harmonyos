#!/usr/bin/env python3
"""Test package for cpufetch 1.07."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{script}"', env="conanrun")
