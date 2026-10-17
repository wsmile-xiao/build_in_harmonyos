#!/usr/bin/env python3
"""Conan test_package — perl-spreadsheet-parseexcel 0.66

L1 smoke test: verify .pm files are present and the module can be loaded.
"""
import os
import glob

from conan import ConanFile


class PerlSpreadsheetParseexcelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No C compilation needed for pure Perl module

    def test(self):
        pkg = self.dependencies["perl-spreadsheet-parseexcel"].package_folder

        # Locate Perl lib directory inside the package
        perl_lib = os.path.join(
            pkg, "data", "service", "hnp", "perl.org", "perl_5.42.0",
            "lib", "site_perl", "5.42.0"
        )

        # 1. Check .pm files exist
        pm_files = glob.glob(os.path.join(perl_lib, "Spreadsheet", "ParseExcel", "**", "*.pm"), recursive=True)
        pm_files += glob.glob(os.path.join(perl_lib, "Spreadsheet", "ParseExcel.pm"))
        assert len(pm_files) >= 15, f"Expected >=15 .pm files, found {len(pm_files)}"

        # 2. Run the test script that loads and exercises the module
        self.run(f'bash "{self.source_folder}/test.sh" "{perl_lib}"', env="conanrun")

        print(f"Perl smoke test passed: found {len(pm_files)} .pm files in package")
        print(f"  Package folder: {pkg}")
        print(f"  Perl lib: {perl_lib}")
