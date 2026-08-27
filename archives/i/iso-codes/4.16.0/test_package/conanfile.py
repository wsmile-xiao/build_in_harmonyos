#!/usr/bin/env python3
"""Conan test_package for iso-codes — data verification test.

iso-codes is a data-only package (JSON files + translations + pkg-config).
This test verifies that the installed data files exist and contain valid content.
"""
import os

from conan import ConanFile


class IsoCodesTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["iso-codes"]
        pkg_folder = pkg.package_folder

        # Run the data verification script
        self.run(f"python3 {os.path.join(self.recipe_folder, 'test_verify.py')} {pkg_folder}",
                 env="conanrun")
