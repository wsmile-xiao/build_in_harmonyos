#!/usr/bin/env python3
"""test_package for ace-window — verifies that ace-window.el was properly installed."""
import os

from conan import ConanFile


class AceWindowTestConan(ConanFile):
    """test_package for ace-window — verifies ace-window.el exists."""
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ace-window"]
        self.run(f"python3 \"{os.path.join(self.source_folder, 'test_ace_window.py')}\" \"{dep.package_folder}\"", env="conanrun")
