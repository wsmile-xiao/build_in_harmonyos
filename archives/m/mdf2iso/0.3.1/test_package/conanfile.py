#!/usr/bin/env python3
"""Conan test_package for mdf2iso 0.3.1."""
import os
import sys

from conan import ConanFile


class Mdf2isoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg_folder, "bin", "mdf2iso")
        script = os.path.join(self.source_folder, "test_mdf2iso.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
