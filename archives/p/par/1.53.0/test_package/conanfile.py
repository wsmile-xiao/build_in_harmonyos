#!/usr/bin/env python3
"""Conan test_package for par 1.53.0 — CLI tool test.

L1 test: verify that the par binary is installed and functional.
Runs test.sh which checks version output and paragraph reflow.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ParTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["par"]
            bin_path = os.path.join(dep.package_folder, "bin", "par")
            test_script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{test_script}" "{bin_path}"', env="conanrun")
