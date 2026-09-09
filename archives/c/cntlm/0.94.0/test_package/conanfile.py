#!/usr/bin/env python3
"""Functional test package for cntlm 0.94.0."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_cntlm.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.recipe_folder, "test_cntlm.py")
            self.run(f'"{sys.executable}" "{script}"', env="conanrun")
