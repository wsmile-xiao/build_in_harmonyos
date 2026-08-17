#!/usr/bin/env python3
"""Conan test_package for premake 5.0.0-beta8 — consumer smoke test.

Runs test_premake.py (real test source file, satisfies L0c) against the
installed premake5 binary: --version assertion + real gmake2 project
generation smoke.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PremakeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["premake"].package_folder
        pbin = os.path.join(pkg, "bin", "premake5")
        test_script = os.path.join(os.path.dirname(__file__), "test_premake.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_premake.py missing: {test_script}")
        if not os.path.isfile(pbin):
            raise ConanException(f"premake5 binary missing: {pbin}")
        self.run(f'python3 "{test_script}" "{pbin}"')
