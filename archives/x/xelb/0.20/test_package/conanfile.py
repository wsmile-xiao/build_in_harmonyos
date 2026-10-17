#!/usr/bin/env python3
"""Conan test_package for xelb 0.20."""
import os
import shlex

from conan import ConanFile


class XelbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_xelb.sh")
        self.run(f"sh {shlex.quote(script)}", env="conanrun")
