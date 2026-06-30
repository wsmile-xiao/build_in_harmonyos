#!/usr/bin/env python3
"""Conan recipe for perl-net-cidr-lite — pure Perl module (Makefile.PL).

Build system: perl Makefile.PL + make + make install
No compiled code — pure Perl, no XS, no C dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PerlnetcidrliteConan(ConanFile):
    name = "perl-net-cidr-lite"
    version = "0.23-r0"
    description = "Perl extension for merging IPv4 or IPv6 CIDR addresses"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-CIDR-Lite"
    url = ""  # CI fills this

    # Pure Perl module — settings present for profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        # PREFIX ensures installation goes to the expected location
        self.run("perl Makefile.PL PREFIX=/usr/local", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
