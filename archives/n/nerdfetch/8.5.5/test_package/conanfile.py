#!/usr/bin/env python3
"""Conan test_package — nerdfetch 8.5.5 smoke test"""
import os
from conan import ConanFile


class NerdfetchTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        nerdfetch_pkg = self.dependencies["nerdfetch"].package_folder
        nerdfetch_bin = os.path.join(nerdfetch_pkg, "bin", "nerdfetch")
        test_script = os.path.join(os.path.dirname(__file__), "test_nerdfetch.sh")
        self.run(f"sh {test_script} {nerdfetch_bin}", env="conanrun")
