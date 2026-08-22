#!/usr/bin/env python3
"""test_package for aview — CLI tool that renders images as ASCII art.

Verifies:
  1. aview binary runs and reports usage (--help)
  2. aview functionally renders a real PPM image to ASCII art via stdout driver
  3. aaflip binary runs and reports usage
  4. asciiview wrapper script is installed
"""
import os

from conan import ConanFile


class AviewTestConan(ConanFile):
    """test_package for aview executable — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")