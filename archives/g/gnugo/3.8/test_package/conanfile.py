#!/usr/bin/env python3
"""Test package — gnugo 3.8."""
import os

from conan import ConanFile


class GnugoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually execute the tested package's binary
        # Run gnugo --version to verify the binary works
        self.run("gnugo --version", env="conanrun")
