#!/usr/bin/env python3
"""Conan test_package for icoutils — verifies installed binaries work."""
import os

from conan import ConanFile


class IcoutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv sets up PATH to include the package's bin directory
        self.run("icotool --version", env="conanrun")
        self.run("wrestool --version", env="conanrun")
