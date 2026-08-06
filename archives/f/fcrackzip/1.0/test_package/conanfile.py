#!/usr/bin/env python3
"""Test package — fcrackzip 1.0.

Verifies the installed fcrackzip binary is functional by running --version.
"""
from conan import ConanFile


class FcrackzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("fcrackzip --version", env="conanrun")
