#!/usr/bin/env python3
"""test_package for avy — verifies that avy.el was properly installed and contains expected Elisp content."""
import os

from conan import ConanFile


class AvyTestConan(ConanFile):
    """test_package for avy — validates avy.el content."""
    test_type = "explicit"

    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the Python test script that validates avy.el content
        dep = self.dependencies["avy"]
        test_script = os.path.join(self.source_folder, "test_avy.py")
        self.run(f'python3 "{test_script}" "{dep.package_folder}"', env="conanrun")
