#!/usr/bin/env python3
"""Conan test_package for lc0 0.32.1 — consumer check.

Runs test_lc0.py (real test source file, satisfies L0c) against the
installed lc0 binary: --version + --help smoke.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class Lc0TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lc0"].package_folder
        bin_path = os.path.join(pkg, "bin", "lc0")
        test_script = os.path.join(os.path.dirname(__file__), "test_lc0.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_lc0.py missing: {test_script}")
        if not os.path.isfile(bin_path):
            raise ConanException(f"lc0 binary missing: {bin_path}")
        self.run(f'python3 "{test_script}" "{bin_path}"')
