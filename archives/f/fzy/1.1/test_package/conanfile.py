#!/usr/bin/env python3
"""Conan test_package for fzy 1.1 — verifies the fzy binary works."""

import os

from conan import ConanFile


class FzyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        fzy = os.path.join(self.dependencies["fzy"].package_folder, "bin", "fzy")
        test_script = os.path.join(self.source_folder, "test_fzy.sh")
        self.run(f'bash "{test_script}" "{fzy}"', env="conanrun")
