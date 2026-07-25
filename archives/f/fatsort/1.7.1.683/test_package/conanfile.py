#!/usr/bin/env python3
"""Conan test_package for fatsort 1.7.1.683."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FatsortTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["fatsort"].package_folder, "bin", "fatsort")
        test_script = os.path.join(self.source_folder, "test.sh")
        if can_run(self):
            self.run(f"bash \"{test_script}\" \"{bin_path}\"", env="conanrun")
