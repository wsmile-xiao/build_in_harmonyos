#!/usr/bin/env python3
"""Conan test_package for perl-net-mpd (Net::MPD).

Verifies that the Net::MPD Perl module can be loaded and reports its version.
"""
import os

from conan import ConanFile


class PerlnetmpdTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use conanrun env which includes PERL5LIB set by package_info()
        # Use single quotes to prevent shell from interpolating $Net::MPD::VERSION
        self.run("perl -e 'use Net::MPD; print qq(Net::MPD version: $Net::MPD::VERSION\\n)'", env="conanrun")
