#!/usr/bin/env python3
"""Conan test_package for cloud-utils — verifies installed scripts are functional."""
import os

from conan import ConanFile


class CloudutilsTestConan(ConanFile):
    settings = ("os", "arch")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must execute the tested package's binary
        test_script = os.path.join(os.path.dirname(__file__), "test_scripts.sh")
        self.run(f"sh {test_script}", env="conanrun")
