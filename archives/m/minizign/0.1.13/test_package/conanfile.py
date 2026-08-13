#!/usr/bin/env python3
"""Conan test package for the minizign CLI."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class MinizignTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping runtime test because this is not a runnable configuration")
            return

        minizign = os.path.join(
            self.dependencies["minizign"].package_folder, "bin", "minizign"
        )
        test_script = os.path.join(self.source_folder, "test_minizign.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{minizign}" "{self.build_folder}"',
            env="conanrun",
        )
