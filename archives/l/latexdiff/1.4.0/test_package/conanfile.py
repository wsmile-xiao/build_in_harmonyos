#!/usr/bin/env python3
"""Conan test package for latexdiff/1.4.0."""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class LatexdiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        test_script = os.path.join(self.source_folder, "test_latexdiff.py")
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
