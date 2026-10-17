#!/usr/bin/env python3
"""Conan test_package for delight 1.7."""
import os
import shlex

from conan import ConanFile


class DelightTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_delight.sh")
        self.run(f"sh {shlex.quote(script)}", env="conanrun")
