#!/usr/bin/env python3
"""Conan test_package for perl-par-dist — Perl L1 test.

Tests that the installed PAR::Dist module can be loaded and used.
Uses test.sh which exercises the module's parse_dist_name() API.
"""
import os
import glob

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlpardistTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_folder = self.dependencies["perl-par-dist"].package_folder
        # Find the site_perl directory containing the .pm files
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Dist.pm"), recursive=True)
        if not pm_files:
            pm_files = glob.glob(os.path.join(pkg_folder, "**", "*.pm"), recursive=True)
        if pm_files:
            dist_pm = pm_files[0]
            # Walk up to find the dir that contains "PAR/"
            perl_lib = os.path.dirname(os.path.dirname(dist_pm))
        else:
            perl_lib = os.path.join(pkg_folder, "lib", "site_perl", "5.42.0")

        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_script} {perl_lib}", env="conanrun")
