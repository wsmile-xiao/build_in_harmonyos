#!/usr/bin/env python3
"""Conan L1 test_package for probcons/1.12 (consumer view)."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class ProbconsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_probcons.py")
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, bindir),
            env="conanrun",
        )
