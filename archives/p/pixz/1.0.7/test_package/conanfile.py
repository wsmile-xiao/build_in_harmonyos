#!/usr/bin/env python3
"""Conan test_package for pixz."""

import os
import sys

from conan import ConanFile


class PixzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pixz"]
        pixz_bin = os.path.join(dep.package_folder, "bin", "pixz")
        test_script = os.path.join(self.source_folder, "test_pixz.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{pixz_bin}" "{self.build_folder}"',
        )
