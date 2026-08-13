#!/usr/bin/env python3
"""Conan test_package for aiohappyeyeballs 2.7.1 — Python library.

Runs test_aiohappyeyeballs.py (real test source file, satisfies L0c)
against the package installed by THIS conan recipe (verifies module path + API).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AiohappyeyeballsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["aiohappyeyeballs"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_aiohappyeyeballs.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_aiohappyeyeballs.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')
