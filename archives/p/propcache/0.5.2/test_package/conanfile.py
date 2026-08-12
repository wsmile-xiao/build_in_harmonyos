#!/usr/bin/env python3
"""Conan test_package for propcache 0.5.2 — Python library.

Runs test_propcache.py (real test source file, satisfies L0c) against the
package installed by THIS conan recipe (verifies module path + core API).
"""
import os

from conan import ConanFile


class PropcacheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["propcache"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_propcache.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_propcache.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')