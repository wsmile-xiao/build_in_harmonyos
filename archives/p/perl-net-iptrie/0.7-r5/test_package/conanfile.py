#!/usr/bin/env python3
"""Conan test_package for perl-net-iptrie — Perl L1 test.

Tests that Net::IPTrie module can be loaded and basic operations work.
Uses test.pl which exercises the module's API.
"""
import os
import glob

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlnetiptrieTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_folder = self.dependencies["perl-net-iptrie"].package_folder
        # Find the site_perl directory containing the .pm files
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "IPTrie.pm"), recursive=True)
        if not pm_files:
            # Fallback: search for any .pm file under the package
            pm_files = glob.glob(os.path.join(pkg_folder, "**", "*.pm"), recursive=True)
        if pm_files:
            # The -I path should be the directory containing the "Net" directory
            iptrie_pm = pm_files[0]
            # Walk up to find the dir that contains "Net/"
            perl_lib = os.path.dirname(os.path.dirname(iptrie_pm))
        else:
            perl_lib = os.path.join(pkg_folder, "lib", "site_perl", "5.42.0")

        test_script = os.path.join(self.source_folder, "test.pl")
        self.run(f'perl -I{perl_lib} {test_script}', env="conanrun")
