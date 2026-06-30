#!/usr/bin/env python3
"""Conan test_package — Net::SFTP::Foreign (pure Perl module).

L1 test: verify the Perl module can be loaded and reports correct version.
Uses Conan 2.x VirtualRunEnv — PERL5LIB is set via runenv_info in the recipe.
"""
from conan import ConanFile


class PerlnetsftpforeignTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PERL5LIB is set via runenv_info in the main recipe
        # Use single quotes to prevent shell variable expansion of $VERSION
        self.run("perl -MNet::SFTP::Foreign -e 'print $Net::SFTP::Foreign::VERSION'", env="conanrun")
