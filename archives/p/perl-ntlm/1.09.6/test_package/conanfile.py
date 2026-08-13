#!/usr/bin/env python3
"""Conan test_package for perl-ntlm (Authen::NTLM).

Tests that the Perl module can be loaded and used via test_ntlm.sh.
"""
import os

from conan import ConanFile


class PerlntlmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-ntlm"]
        perl_lib = os.path.join(dep.package_folder, "lib", "perl5")
        self.output.info("Testing with Perl lib path: " + perl_lib)
        # Run the test script which verifies module loading + NTLM functions
        self.run("PERL_LIB=" + perl_lib + " sh " + os.path.join(self.source_folder, "test_ntlm.sh"))
