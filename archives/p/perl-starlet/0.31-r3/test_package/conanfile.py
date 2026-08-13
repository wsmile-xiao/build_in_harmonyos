#!/usr/bin/env python3
"""Conan test_package — perl-starlet 0.31-r3 (Perl module L1 test).

Verifies that the Starlet Perl module is installed and can be loaded.
"""
import os

from conan import ConanFile


class PerlStarletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The Perl module is installed under the Conan package folder
        # at data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
        # We need to set PERL5LIB to find it
        pkg_folder = self.dependencies["perl-starlet"].package_folder
        perllib = os.path.join(
            pkg_folder,
            "data", "service", "hnp", "perl.org", "perl_5.42.0",
            "lib", "site_perl", "5.42.0",
        )
        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        self.run(f'sh "{test_script}" "{perllib}"')
