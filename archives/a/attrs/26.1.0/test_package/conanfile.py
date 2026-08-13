#!/usr/bin/env python3
"""Conan test_package for attrs 26.1.0 — Python library.

Runs test_attrs.py (real test source file, satisfies L0c) against the package
installed by THIS conan recipe. Upstream pytest subset runs in build().
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AttrsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["attrs"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_attrs.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_attrs.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')