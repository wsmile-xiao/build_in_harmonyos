#!/usr/bin/env python3
"""Conan test_package for perl-spreadsheet-xlsx 0.18.

Verifies that Spreadsheet::XLSX can be loaded and basic XLSX parsing works.
Test logic is in test_spreadsheet_xlsx.sh (L0c compliant: .sh source file).
"""
import os

from conan import ConanFile


class PerlSpreadsheetXlsxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-spreadsheet-xlsx"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(self.source_folder, "test_spreadsheet_xlsx.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"')
