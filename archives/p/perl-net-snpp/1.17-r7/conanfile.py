#!/usr/bin/env python3
"""Conan recipe — Net::SNPP (Simple Network Pager Protocol Client) Perl module.

This is a pure Perl module built with ExtUtils::MakeMaker (perl Makefile.PL).
No C/XS compilation, no static linking needed — just .pm file installation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetsnppConan(ConanFile):
    name = "perl-net-snpp"
    version = "1.17-r7"
    description = "Simple Network Pager Protocol Client — pure Perl module"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-SNPP"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Net::Cmd is part of libnet; available in system Perl
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install Perl module files to package
        copy(self, "*.pm", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib/perl5"))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers
        perl5lib = os.path.join(self.package_folder, "lib/perl5")
        self.runenv_info.append("PERL5LIB", perl5lib)
