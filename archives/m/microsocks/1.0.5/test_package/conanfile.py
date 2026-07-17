#!/usr/bin/env python3
"""Test package for microsocks 1.0.5."""

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("microsocks --help 2>&1 | head -5", env="conanrun")