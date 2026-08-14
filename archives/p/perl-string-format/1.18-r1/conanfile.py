#!/usr/bin/env python3
"""Conan recipe — perl-string-format 1.18-r1 (pure Perl module).

String::Format: sprintf-like string formatting with arbitrary format definitions.
Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlstringformatConan(ConanFile):
    name = "perl-string-format"
    version = "1.18-r1"
    description = "String::Format - sprintf-like string formatting with arbitrary format definitions"
    license = "MIT"
    homepage = "https://metacpan.org/dist/String-Format"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # Pure Perl module: use INSTALL_BASE for predictable install layout
        self.run("perl Makefile.PL INSTALL_BASE=perl_install", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to the INSTALL_BASE directory, then copy to package folder
        self.run("make install", cwd=self.source_folder)
        install_dir = os.path.join(self.source_folder, "perl_install")
        if os.path.isdir(install_dir):
            copy(self, "*", src=install_dir, dst=self.package_folder)

    def package_info(self):
        # Pure Perl module — no C library to link
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the Perl module
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib/perl5"))
