#!/usr/bin/env python3
"""test_package for avy — verifies that avy.el was properly installed."""
import os

from conan import ConanFile


class AvyTestConan(ConanFile):
    """test_package for avy — verifies avy.el exists."""
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run test script to verify avy.el exists and content is valid
        dep = self.dependencies["avy"]
        self.run(f"python3 \"{os.path.join(self.source_folder, 'test_avy.py')}\" \"{dep.package_folder}\"", env="conanrun")
