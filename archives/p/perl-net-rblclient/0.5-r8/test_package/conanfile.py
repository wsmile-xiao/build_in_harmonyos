#!/usr/bin/env python3
"""Conan test_package — perl-net-rblclient 0.5-r8 (Pure Perl module).

Tests that the installed Perl module can be loaded successfully.
"""
import os

from conan import ConanFile


class PerlnetrblclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PERL5LIB is set by the package's runenv_info
        # Verify the Perl module can be loaded
        self.run('perl -e "use Net::RBLClient; print qq(Net::RBLClient loaded OK\\n)"', env="conanrun")
