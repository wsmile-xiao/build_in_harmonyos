#!/usr/bin/env python3
"""Conan recipe — perl-regexp-tr 0.05 (Regexp::Tr)

Pure-Perl module using ExtUtils::MakeMaker (EUMM).
Run-time-compiled tr/// objects.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRegexpTrConan(ConanFile):
    name = "perl-regexp-tr"
    version = "0.05"
    description = "Run-time-compiled tr/// objects (Regexp::Tr)"
    license = "unknown"
    homepage = "https://metacpan.org/dist/Regexp-Tr"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # EUMM: perl Makefile.PL + make (run in source folder)
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built .pm files from blib/lib to lib/perl5
        copy(self, "*.pm", src=os.path.join(self.source_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        # Set PERL5LIB so consumers can find the module
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
