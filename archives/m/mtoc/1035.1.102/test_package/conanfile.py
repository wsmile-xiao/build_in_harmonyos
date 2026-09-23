#!/usr/bin/env python3
"""Conan test package for the mtoc command-line converter."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class MtocTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["mtoc"].package_folder
        mtoc = os.path.join(package_folder, "bin", "mtoc")
        test_script = os.path.join(self.source_folder, "test_mtoc.py")
        work_folder = os.path.join(self.build_folder, "mtoc-functional-test")
        self.run(
            f'"{sys.executable}" "{test_script}" "{mtoc}" "{work_folder}"',
            env="conanrun",
        )
