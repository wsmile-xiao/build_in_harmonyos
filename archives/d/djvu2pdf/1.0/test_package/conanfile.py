#!/usr/bin/env python3
"""Test package for djvu2pdf — verifies installed scripts are present and functional."""
import os

from conan import ConanFile


class Djvu2PdfTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["djvu2pdf"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact — verify scripts are present,
        # executable, have correct shebang, and pass syntax checks.
        self.run(f"bash test_djvu2pdf.sh \"{bin_dir}\"", env="conanrun")
        self.output.info("djvu2pdf: OK")
