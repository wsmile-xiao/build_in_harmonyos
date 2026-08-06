#!/usr/bin/env python3
"""Test package for adwaita-fonts-mono 50.

Delegates font validation to test_fonts.py (standalone test source file).
"""
import os
import sys
from conan import ConanFile


class AdwaitaFontsMonoTestConan(ConanFile):
    # Font validation package — no compilation, no settings needed
    # test_package validates TTF files exist, non-empty, and have correct magic

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the font directory via dependency
        dep = self.dependencies["adwaita-fonts-mono"]
        font_dir = os.path.join(dep.package_folder, "share", "fonts", "AdwaitaMono")

        # Run the standalone test script
        test_script = os.path.join(self.source_folder, "test_fonts.py")
        self.run(f"{sys.executable} {test_script} {font_dir}")