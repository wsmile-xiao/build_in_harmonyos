#!/usr/bin/env python3
"""Conan test_package for babeld 1.13.1.

babeld is a standalone binary (Babel routing protocol daemon).
The test runs test_babeld.sh which verifies:
  1. babeld -V outputs correct version
  2. babeld -h prints usage syntax
"""
import os

from conan import ConanFile


class BabeldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate babeld binary via dependency package folder
        dep = self.dependencies["babeld"]
        bin_path = os.path.join(str(dep.package_folder), "usr", "local", "bin", "babeld")
        test_script = os.path.join(self.source_folder, "test_babeld.sh")
        self.run(f'sh "{test_script}" "{bin_path}"')
