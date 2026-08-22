#!/usr/bin/env python3
"""Conan test_package — pdfsandwich 0.1.7

Verifies the pdfsandwich binary is functional by running `pdfsandwich -version`.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PdfsandwichTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Run the pdfsandwich binary directly to verify it works
        self.run("pdfsandwich -version", env="conanrun")
