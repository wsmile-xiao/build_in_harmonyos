#!/usr/bin/env python3
"""Conan test_package — Perl module test (L1).

Verifies that Net::SNMP is properly packaged and loadable.
"""
import os

from conan import ConanFile


class PerlnetsnmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency (Conan 2.x API)
        pkg_folder = self.dependencies["perl-net-snmp"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib")
        self.output.info("Using PERL5LIB={}".format(perl_lib))

        # Run test script from source folder directly
        test_script = os.path.join(self.source_folder, "test_snmp.sh")
        self.run('PERL5LIB="{}" sh "{}"'.format(perl_lib, test_script), env="conanrun")
