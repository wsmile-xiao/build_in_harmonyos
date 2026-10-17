#!/usr/bin/env python3
"""Conan test_package for gnu-typist 2.10.1 smoke test."""
import os
from conan import ConanFile
from conan.tools.build import can_run


class GnutypistTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(os.path.dirname(__file__), "test_gnu_typist.sh")
            self.run(f'sh "{script}"', env="conanrun")
