#!/usr/bin/env python3
"""Conan test_package for jp2a 1.3.3."""

import os

from conan import ConanFile


class Jp2aTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        jp2a = os.path.join(self.dependencies["jp2a"].package_folder, "bin", "jp2a")
        self.run(f'"{jp2a}" --version', env="conanrun")
        self.run(f'"{jp2a}" --help', env="conanrun")
