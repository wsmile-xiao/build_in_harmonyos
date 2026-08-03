#!/usr/bin/env python3
"""Conan test_package for bltool 0.2.4 — verifies the failed-adaptation record."""

import os
import sys

from conan import ConanFile


class BltoolTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_failed_archive.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"')
