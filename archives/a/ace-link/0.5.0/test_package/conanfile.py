#!/usr/bin/env python3
"""test_package for ace-link — verifies that ace-link.el was properly installed."""
import os

from conan import ConanFile


class AceLinkTestConan(ConanFile):
    """test_package for ace-link — verifies ace-link.el exists."""
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ace-link"]
        self.run(f"python3 \"{os.path.join(self.source_folder, 'test_ace_link.py')}\" \"{dep.package_folder}\"", env="conanrun")
