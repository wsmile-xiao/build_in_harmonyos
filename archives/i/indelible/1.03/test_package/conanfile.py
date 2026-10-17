#!/usr/bin/env python3
"""Test package for indelible 1.03 — runs the real binary."""

import os
import sys

from conan import ConanFile


class IndelibleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "indelible")
        script = os.path.join(self.recipe_folder, "test_indelible.py")
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, executable),
            env="conanrun",
        )
