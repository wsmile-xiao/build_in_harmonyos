#!/usr/bin/env python3
"""Conan test_package for cpplint — verifies the installed cpplint command works.

This test runs `cpplint --version` to verify the installed package is functional.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class CpplintTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # No build step needed for a Python tool test
        pass

    def test(self):
        # Use the Conan-generated run environment to find the cpplint binary
        # The VirtualRunEnv generator sets up PATH and PYTHONPATH
        self.run("cpplint --version", env="conanrun")
