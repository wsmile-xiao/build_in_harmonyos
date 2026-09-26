#!/usr/bin/env python3
"""Conan test_package — consumer test for the packaged zope.interface.

Runs the standalone test source test_zi.py (real public-API calls, R34)
with the packaged site-packages on PYTHONPATH via the conanrun env.
"""
import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["zope.interface"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_zi.py")
        self.run(f'"{sys.executable}" "{test_script}" "{site}"',
                 env="conanrun")
