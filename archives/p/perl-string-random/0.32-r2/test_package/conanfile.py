#!/usr/bin/env python3
"""Conan test_package — perl-string-random 0.32-r2 (pure Perl module).

Verifies that String::Random can be loaded and used to generate
random strings from a pattern.
"""
import os

from conan import ConanFile


class PerlStringRandomTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency
        deps = self.dependencies["perl-string-random"]
        pkg_folder = deps.package_folder
        # The module is installed under data/service/hnp/perl.org/.../site_perl/...
        perl_lib = os.path.join(pkg_folder, "data", "service", "hnp",
                                "perl.org", "perl_5.42.0", "lib",
                                "site_perl", "5.42.0")

        # Verify String::Random.pm exists
        random_pm = os.path.join(perl_lib, "String", "Random.pm")
        if not os.path.exists(random_pm):
            # Search in versioned subdirectories
            for root, _, files in os.walk(pkg_folder):
                if "Random.pm" in files and "String" in root:
                    perl_lib = root.rsplit("/String", 1)[0]
                    break

        # Run the test script with PERL5LIB set
        self.run('PERL5LIB="{}" sh test_string_random.sh'.format(perl_lib))
