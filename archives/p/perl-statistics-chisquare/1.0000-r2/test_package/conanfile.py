#!/usr/bin/env python3
"""Conan test_package — Statistics::ChiSquare (pure Perl module)."""
import os
import glob

from conan import ConanFile


class PerlstatisticschisquareTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-statistics-chisquare"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Statistics", "ChiSquare.pm"), recursive=True)
        if not pm_files:
            raise Exception("Statistics/ChiSquare.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        self.run(f'sh "{test_script}" "{perl_lib_dir}"')
