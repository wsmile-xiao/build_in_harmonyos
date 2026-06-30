#!/usr/bin/env python3
"""Conan test_package for perl-net-jabber-bot 2.1.7-r0.

Verifies the Pure Perl module can be loaded via `perl -MNet::Jabber::Bot`.
"""
import os

from conan import ConanFile


class PerlnetjabberbotTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["perl-net-jabber-bot"]
        pkg_folder = str(dep.package_folder)
        # The module is installed to site_perl under the package folder
        perl_lib = os.path.join(pkg_folder, "data", "service", "hnp", "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0")
        # Include user's existing Perl lib directories for dependencies (Moose, Net::Jabber, etc.)
        user_perl_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0:/storage/Users/currentUser/usr/local/lib/perl5"
        # Run perl with PERL5LIB set to include both the Conan package and user's Perl modules
        full_perl5lib = f"{perl_lib}:{user_perl_lib}"
        self.run(f'PERL5LIB="{full_perl5lib}" perl -MNet::Jabber::Bot -e \'print "Net::Jabber::Bot loaded OK\\n"\'')
