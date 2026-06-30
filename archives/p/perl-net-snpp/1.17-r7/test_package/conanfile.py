#!/usr/bin/env python3
"""Conan test_package — Net::SNPP Perl module L1 test.

Tests that the Net::SNPP Perl module can be loaded via PERL5LIB.
"""
import os

from conan import ConanFile


class PerlnetsnppTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Use conanrun env which includes PERL5LIB from package_info
        self.run("perl -MNet::SNPP -e 'print qq(Net::SNPP loaded OK, version: $Net::SNPP::VERSION\\n)'", env="conanrun")
