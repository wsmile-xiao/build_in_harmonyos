#!/usr/bin/env python3
"""Conan test_package — perl-net-ipv4addr 0.10-r7

Tests that the Perl module Net::IPv4Addr can be loaded and used.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class Perlnetipv4AddrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: Module loads successfully
        self.run('perl -MNet::IPv4Addr -e "print \'Net::IPv4Addr loaded ok\\n\'"', env="conanrun")

        # Test 2: Basic IPv4 address parsing
        self.run(
            'perl -MNet::IPv4Addr -e \''
            'my ($ip, $cidr) = Net::IPv4Addr::ipv4_parse("192.168.1.1/24"); '
            'die "parse failed" unless $ip eq "192.168.1.1" && $cidr eq "24"; '
            'print "ipv4_parse ok\\n"\'',
            env="conanrun",
        )

        # Test 3: IPv4 network membership check
        self.run(
            'perl -MNet::IPv4Addr -e \''
            'my $r = Net::IPv4Addr::ipv4_in_network("192.168.1.0/24", "192.168.1.5"); '
            'die "network check failed" unless $r; '
            'print "ipv4_in_network ok\\n"\'',
            env="conanrun",
        )

        # Test 4: IPv4 address validation
        self.run(
            'perl -MNet::IPv4Addr -e \''
            'die "chkip failed" unless Net::IPv4Addr::ipv4_chkip("10.0.0.1"); '
            'print "ipv4_chkip ok\\n"\'',
            env="conanrun",
        )

        # Test 5: IPv4 network address calculation
        self.run(
            'perl -MNet::IPv4Addr -e \''
            'my ($net, $cidr) = Net::IPv4Addr::ipv4_network("192.168.1.100/24"); '
            'die "network calc failed" unless $net eq "192.168.1.0"; '
            'print "ipv4_network ok\\n"\'',
            env="conanrun",
        )
