#!/usr/bin/env python3
"""Conan test_package — verify gws bash script is installed and runnable."""
from conan import ConanFile


class GwsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify gws is installed and can show help (doesn't require workspace)
        self.run("gws --help", env="conanrun")
