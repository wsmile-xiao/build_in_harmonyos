#!/usr/bin/env python3
"""Conan test_package for cramfs 1.1.

Tests the actual cramfs binaries (mkcramfs and cramfsck) by creating
a cramfs image from a test directory and verifying it with cramfsck.
"""
import os

from conan import ConanFile


class CramfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {script}", env="conanrun")
