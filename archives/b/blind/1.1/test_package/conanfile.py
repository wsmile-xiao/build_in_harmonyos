#!/usr/bin/env python3
"""Conan test_package for blind 1.1 — executable smoke test."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class BlindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bin_path = os.path.join(self.dependencies["blind"].package_folder, "bin", "blind-arithm")
        script_path = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script_path}" "{bin_path}"', env="conanrun")
