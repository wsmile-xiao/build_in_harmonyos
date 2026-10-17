#!/usr/bin/env python3
"""Conan test_package — adobe-source-code-pro 2.042u L1 smoke test.

Asserts 7 upright .ttf files exist in share/fonts/SourceCodePro/, non-empty,
with TTF magic and matching sha256 baselines.
"""

from conan import ConanFile


class AdobeSourceCodeProTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adobe-source-code-pro"]
        pkg_folder = dep.package_folder
        self.run(f"python3 test_fonts.py {pkg_folder}", env="conanrun")
