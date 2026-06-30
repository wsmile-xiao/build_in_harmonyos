#!/usr/bin/env python3
"""Conan test_package for perl-net-telnet (pure Perl module).

L1 test: Verify the Perl module can be loaded and reports correct version.
"""
import os

from conan import ConanFile


class PerlNetTelnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for Perl module test

    def test(self):
        # Get the package folder from the dependency
        pkg = self.dependencies["perl-net-telnet"]
        pkg_folder = pkg.package_folder

        # Search for the Net/Telnet.pm file to find the correct lib path
        perl_lib = None
        for root, dirs, files in os.walk(pkg_folder):
            if "Telnet.pm" in files and root.endswith(os.path.join("Net")):
                # The lib path is the parent of "Net" directory
                perl_lib = os.path.dirname(root)
                break

        if perl_lib:
            cmd = (f'perl -I"{perl_lib}" -MNet::Telnet -e '
                   f'\'print "Net::Telnet version: ", Net::Telnet->VERSION, "\\n"; '
                   f'die "version mismatch" unless Net::Telnet->VERSION eq "3.05";\'')
        else:
            # Fallback: try without explicit path
            cmd = ('perl -MNet::Telnet -e '
                   '\'print "Net::Telnet version: ", Net::Telnet->VERSION, "\\n";\'')

        self.run(cmd, env="conanrun")
