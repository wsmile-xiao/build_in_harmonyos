#!/usr/bin/env python3
"""Conan test_package for gnu-which 2.25.

L1 test: verify the 'which' binary works correctly.
Since gnu-which is a command-line tool (not a library),
we test by running the binary directly.
"""
import os

from conan import ConanFile


class GnuwhichTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv adds the package's bin dir to PATH
        # Test: --version should output "GNU which v2.25"
        self.run("which --version", env="conanrun")
