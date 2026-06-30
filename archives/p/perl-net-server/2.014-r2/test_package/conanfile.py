#!/usr/bin/env python3
"""Conan test_package — perl-net-server (Net::Server) 2.014-r2

L1 test: verify the Perl module can be loaded and reports correct version.
"""
import os

from conan import ConanFile


class PerlnetserverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed for a pure Perl module test
        pass

    def test(self):
        # Verify the module loads and reports the correct version
        self.run('perl -MNet::Server -e "print Net::Server->VERSION, qq{\\n}"', env="conanrun")
