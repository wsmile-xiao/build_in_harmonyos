#!/usr/bin/env python3
"""Conan test_package — ae_fonts_mono 1.0

Data-only package test: delegates the real consumer verification to the
standalone test source file test_font_package.py (invoked via self.run()).
The test source checks that 10x21.bdf / 10x21.pcf are installed in the
package's share/fonts/ae_fonts_mono/ directory with correct sizes, BDF
metadata, PCF magic and the pkg-config fontdir declaration.
"""
import os

from conan import ConanFile


class AefontsmonoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ae_fonts_mono"]
        pkg_root = pkg.package_folder

        # Run the standalone consumer test source against the installed
        # package. test_font_package.py performs all real assertions and
        # exits non-zero on any failure (L0d: self.run() invoked).
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_font_package.py")
        self.run(f"python3 {test_script} {pkg_root}")
