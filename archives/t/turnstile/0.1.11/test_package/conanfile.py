#!/usr/bin/env python3
"""Conan test_package recipe for turnstile 0.1.11."""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["turnstile"].package_folder
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_turnstile.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
