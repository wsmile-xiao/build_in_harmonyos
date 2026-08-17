#!/usr/bin/env python3
"""Conan test_package — Perl module Number::Compare.

Verifies the installed Perl module can be loaded and used.
"""
import os
import shutil

from conan import ConanFile


class PerlNumberCompareTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Copy static test source to build folder
        test_src = os.path.join(self.recipe_folder, "test_compare.pl")
        test_dst = os.path.join(self.build_folder, "test_compare.pl")
        try:
            shutil.copy2(test_src, test_dst)
        except shutil.SameFileError:
            pass  # build_folder == recipe_folder

    def test(self):
        # Get the Perl lib directory from the dependency package
        dep = self.dependencies["perl-number-compare"]
        pkg_folder = dep.package_folder
        perl_lib = os.path.join(pkg_folder, "lib")

        self.output.info(f"Package folder: {pkg_folder}")
        self.output.info(f"Perl lib: {perl_lib}")

        test_script = os.path.join(self.build_folder, "test_compare.pl")
        self.run(f'perl -I"{perl_lib}" {test_script}')
