#!/usr/bin/env python3
"""Conan test_package for htop 3.4.1.

Verifies the htop binary is installed and functional.
R34: test must exercise the actual package binary.
"""
from conan import ConanFile


class HtopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: run the actual htop binary to verify it works
        self.run("htop --version", env="conanrun")
