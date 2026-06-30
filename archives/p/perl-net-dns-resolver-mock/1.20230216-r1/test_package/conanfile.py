#!/usr/bin/env python3
"""Conan test_package — Perl module Net::DNS::Resolver::Mock.

Verifies the installed Perl module can be loaded and used.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlnetdnsresolvermockTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the dependency's package folder to find the Perl module
        dep = self.dependencies["perl-net-dns-resolver-mock"]
        perl_lib = os.path.join(dep.package_folder, "lib")
        test_script = os.path.join(self.source_folder, "test.pl")
        # Use -I to add the module path directly (more reliable than PERL5LIB)
        self.run(f'perl -I"{perl_lib}" {test_script}')
