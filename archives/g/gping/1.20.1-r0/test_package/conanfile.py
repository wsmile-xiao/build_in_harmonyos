#!/usr/bin/env python3
"""Conan test_package for gping — verifies the binary works.

L1 official test: runs `gping --version` to verify the binary
is correctly built and functional.
"""
import os

from conan import ConanFile


class GpingTestConan(ConanFile):
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # Run gping --version to verify the binary works
        # conanrun env includes the package's bin/ in PATH
        self.run("gping --version", env="conanrun")
