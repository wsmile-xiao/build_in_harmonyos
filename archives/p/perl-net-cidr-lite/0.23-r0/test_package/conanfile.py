#!/usr/bin/env python3
"""Conan test_package for perl-net-cidr-lite — Perl L1 test.

Tests that the installed Net::CIDR::Lite module can be loaded and used.
"""
from conan import ConanFile


class PerlnetcidrliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use Net::CIDR::Lite; '
            'my $cidr = Net::CIDR::Lite->new; '
            '$cidr->add("192.168.0.0/16"); '
            'my @list = $cidr->list; '
            'die "test failed" unless @list == 1; '
            'print "Net::CIDR::Lite test OK\\n";'
        )
        self.run(f'perl -e \'{test_script}\'')
