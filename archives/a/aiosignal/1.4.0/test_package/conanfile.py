#!/usr/bin/env python3
"""Conan test_package for aiosignal 1.4.0 — Python library.

Runs test_aiosignal.py (real test source file, satisfies L0c) against the
package installed by THIS conan recipe. Adds BOTH aiosignal and frozenlist
site-packages to PYTHONPATH (aiosignal imports frozenlist at module load).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AiosignalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["aiosignal"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # aiosignal imports frozenlist at module load — add its path too
        if "frozenlist" in self.dependencies:
            fl_site = os.path.join(
                self.dependencies["frozenlist"].package_folder,
                "lib", "python3.12", "site-packages")
            site = os.pathsep.join([site, fl_site])
        test_script = os.path.join(os.path.dirname(__file__), "test_aiosignal.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_aiosignal.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')