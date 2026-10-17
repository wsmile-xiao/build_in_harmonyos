#!/usr/bin/env python3
"""Conan test_package — adwaita-fonts 50.0 L1 smoke test.

Asserts 6 .ttf files exist in share/fonts/Adwaita/, non-empty, with TTF magic.
"""

from conan import ConanFile


class AdwaitaFontsTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adwaita-fonts"]
        pkg_folder = dep.package_folder
        self.run(f"python3 test_fonts.py {pkg_folder}", env="conanrun")