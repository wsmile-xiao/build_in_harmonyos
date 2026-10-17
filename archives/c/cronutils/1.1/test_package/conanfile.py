#!/usr/bin/env python3
"""Consumer test recipe for cronutils 1.1."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CronutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("cronutils consumer test skipped: target cannot run")
            return

        package = self.dependencies["cronutils"].package_folder
        bin_dir = os.path.join(package, "bin")
        script = os.path.join(self.recipe_folder, "test_cronutils.py")
        self.run(
            f'"{sys.executable}" "{script}" "{bin_dir}"',
            env="conanrun",
        )
