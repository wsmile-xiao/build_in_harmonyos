#!/usr/bin/env python3
"""Conan test_package — Net::DNS::Resolver::Programmable (Perl module).

Verifies the Perl module can be loaded and used.
"""
from conan import ConanFile


class PerlnetdnsresolverprogrammableTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the Perl module can be loaded
        self.run('perl -e "use Net::DNS::Resolver::Programmable; print \\"OK\\n\\""', env="conanrun")
