#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) projects.

Build system: perl Makefile.PL && make && make install
This is a pure-Perl module (no C compilation required).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlSpreadsheetParseexcelConan(ConanFile):
    name = "perl-spreadsheet-parseexcel"
    version = "0.66"
    description = "Spreadsheet::ParseExcel - Read information from an Excel file"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Spreadsheet-ParseExcel"
    url = ""  # CI fills this

    # R32: settings.os 判断必须 in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"

    # Perl EUMM builds in-source
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependencies (Perl modules, not managed by Conan):
        # - OLE::Storage_Lite >= 0.19
        # - Crypt::RC4 (optional, for encryption)
        # - Digest::Perl::MD5 (optional, for encryption)
        # - IO::Scalar (optional)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl EUMM build: must run in source folder where Makefile.PL exists
        src = self.source_folder
        self.run(f'cd "{src}" && perl Makefile.PL', env="conanbuild")
        self.run(f'cd "{src}" && make -j1', env="conanbuild")

    def package(self):
        src = self.source_folder
        # Install to DESTDIR for staging
        self.run(f'cd "{src}" && make install DESTDIR="{self.package_folder}"', env="conanbuild")

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["data"]
