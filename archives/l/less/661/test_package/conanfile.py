#!/usr/bin/env python3
"""Conan test_package for less 661.

Verifies the less binary is installed and functional.
R34: test must exercise the actual package binary.
"""
from conan import ConanFile


class LessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: run the actual less binary to verify it works
        self.run("less --version", env="conanrun")
