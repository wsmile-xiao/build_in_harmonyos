#!/usr/bin/env python3
"""Test package for convmv 2.06."""

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("convmv --help 2>&1 | head -n 10", env="conanrun")