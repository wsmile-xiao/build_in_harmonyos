#!/usr/bin/env python3
"""Conan recipe for perl-net-iptrie (Net::IPTrie) — pure Perl module.

Build system: ExtUtils::MakeMaker (perl Makefile.PL → make → make install)
This is a pure Perl module with no C/C++ code.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetiptrieConan(ConanFile):
    name = "perl-net-iptrie"
    version = "0.7-r5"
    description = "Perl module for building IPv4 and IPv6 address space hierarchies (Net::IPTrie)"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/Net-IPTrie"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # Perl module build: perl Makefile.PL → make
        # Use PREFIX=/usr so install paths are clean under DESTDIR
        self.run("perl Makefile.PL PREFIX=/usr INSTALLDIRS=site", cwd=src_dir)
        self.run("make", cwd=src_dir)

    def package(self):
        src_dir = self.source_folder
        # Install to Conan package folder via DESTDIR
        self.run("make install DESTDIR={}".format(self.package_folder), cwd=src_dir)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries
        self.cpp_info.libs = []
        # Find the site_perl lib path for consumers
        pkg = self.package_folder
        pm_files = glob.glob(os.path.join(pkg, "**", "IPTrie.pm"), recursive=True)
        if pm_files:
            perl_lib = os.path.dirname(os.path.dirname(pm_files[0]))
            self.conf_info.define("perl5lib", perl_lib)
