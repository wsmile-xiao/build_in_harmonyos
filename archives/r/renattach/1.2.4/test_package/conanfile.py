#!/usr/bin/env python3
"""Conan test package for the renattach command-line filter."""

import os
import sys

from conan import ConanFile


class RenattachTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["renattach"].package_folder,
            "bin",
            "renattach",
        )
        script = os.path.join(self.source_folder, "test_renattach.py")
        self.run(
            f'"{sys.executable}" "{script}" "{binary}"',
            env="conanrun",
        )
