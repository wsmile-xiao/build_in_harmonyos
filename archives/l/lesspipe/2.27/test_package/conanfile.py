#!/usr/bin/env python3
"""Conan test package for lesspipe/2.27."""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class LesspipeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        test_script = os.path.join(self.source_folder, "test_lesspipe.py")
        self.run(f'"{sys.executable}" "{test_script}" "{pkg}"', env="conanrun")
