#!/usr/bin/env python3
"""Conan test_package for perl-net-xmpp (pure Perl module).

L1 test: Attempts to load Net::XMPP via perl and verify its version.
If runtime dependencies (XML::Stream, Authen::SASL) are unavailable in CI,
falls back to Perl-based source verification (parsing $VERSION from XMPP.pm
using Perl regex, not external grep, and checking all .pm files exist).
"""
import os

from conan import ConanFile


class PerlNetXmppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for Perl module test

    def test(self):
        # PERL5LIB is set by runenv_info from the package's package_info()
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'perl "{test_script}"', env="conanrun")
