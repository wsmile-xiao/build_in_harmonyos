#!/usr/bin/env python3
"""Conan test_package — adobe-source-sans 3.052 L1 smoke test.

Asserts 14 .ttf files exist in share/fonts/SourceSans3/, non-empty, with TTF magic.
"""

from conan import ConanFile


class AdobeSourceSansTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adobe-source-sans"]
        pkg_folder = dep.package_folder
        self.run(f"python3 test_fonts.py {pkg_folder}", env="conanrun")
