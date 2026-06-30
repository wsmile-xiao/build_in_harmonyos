#!/usr/bin/env python3
"""Conan test_package — perl-net-openssh 0.84-r1

Tests that the Perl module Net::OpenSSH can be loaded and used.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class PerlnetopensshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: Module loads successfully
        self.run('perl -MNet::OpenSSH -e "print \'Net::OpenSSH loaded ok\\n\'"', env="conanrun")

        # Test 2: Version check
        self.run(
            'perl -MNet::OpenSSH -e \''
            'die "version mismatch" unless $Net::OpenSSH::VERSION eq "0.84"; '
            'print "version 0.84 ok\\n"\'',
            env="conanrun",
        )

        # Test 3: Constants module loads
        self.run(
            'perl -MNet::OpenSSH::Constants -e "print \'Constants loaded ok\\n\'"',
            env="conanrun",
        )

        # Test 4: ShellQuoter module loads
        self.run(
            'perl -MNet::OpenSSH::ShellQuoter -e "print \'ShellQuoter loaded ok\\n\'"',
            env="conanrun",
        )

        # Test 5: ConnectionCache module loads
        self.run(
            'perl -MNet::OpenSSH::ConnectionCache -e "print \'ConnectionCache loaded ok\\n\'"',
            env="conanrun",
        )
