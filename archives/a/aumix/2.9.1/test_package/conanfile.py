#!/usr/bin/env python3
"""Conan test_package — aumix 2.9.1 L1 test.

Tests that the aumix binary is installed and functional.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class AumixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Use conanrun environment which sets PATH to include package bin/
        self.run("aumix -h", env="conanrun")
