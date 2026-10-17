#!/usr/bin/env python3
"""Conan test_package — adwaita-fonts-sans 50

Data-only package test: verifies that the Adwaita Sans .ttf font files
exist in the package's share/fonts/Adwaita/ directory by executing a
shell script test.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AdwaitaFontsSansTestConan(ConanFile):
    # Font validation is data-only; no compilation settings needed

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder from the dependency
        pkg = self.dependencies["adwaita-fonts-sans"]
        pkg_root = pkg.package_folder

        fonts_dir = os.path.join(pkg_root, "share", "fonts", "Adwaita")

        # Run the test script to verify font files
        test_script = os.path.join(self.source_folder, "test_fonts.sh")
        self.run(f"chmod +x {test_script} && {test_script} {fonts_dir}", cwd=self.source_folder)

        # Verify the OFL-1.1 license file was installed to share/licenses/
        license_path = os.path.join(
            pkg_root, "share", "licenses", "adwaita-fonts-sans", "LICENSE"
        )
        if not os.path.isfile(license_path):
            raise ConanException(f"FAIL: LICENSE not installed: {license_path}")
        with open(license_path, "r", encoding="utf-8", errors="replace") as fh:
            license_text = fh.read()
        if "SIL OPEN FONT LICENSE" not in license_text:
            raise ConanException("FAIL: installed LICENSE is not SIL OFL-1.1")
        self.output.info(f"  OK: LICENSE installed at {license_path}")

        self.output.info("adwaita-fonts-sans test passed: all fonts verified")