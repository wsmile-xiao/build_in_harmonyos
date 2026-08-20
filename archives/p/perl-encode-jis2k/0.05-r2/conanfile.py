#!/usr/bin/env python3
"""Conan recipe — Encode::JIS2K Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that provides
JIS X 0212 and JIS X 0213 encoding support for Perl.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlEncodeJIS2KConan(ConanFile):
    name = "perl-encode-jis2k"
    version = "0.05-r2"
    description = "Perl XS extension providing JIS X 0212 and JIS X 0213 encoding support"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Encode-JIS2K"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — only Perl core modules (Encode >= 1.41)
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl XS module build: Makefile.PL generates Makefile, then make compiles C/XS code
        # R1: 参数最少化 — no PREFIX needed, use Perl defaults
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts to package folder in standard layout
        # .so goes to lib/auto/Encode/JIS2K/ (Perl auto path)
        # .pm goes to lib/Encode/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "JIS2K.so",
             src=os.path.join(blib_arch, "auto", "Encode", "JIS2K"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Encode", "JIS2K"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Encode", "JIS2K"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Encode", "JIS2K"))
        copy(self, "JIS2K.pm",
             src=os.path.join(blib_lib, "Encode"),
             dst=os.path.join(self.package_folder, "lib", "Encode"))
        copy(self, "2022JP3.pm",
             src=os.path.join(blib_lib, "Encode", "JIS2K"),
             dst=os.path.join(self.package_folder, "lib", "Encode", "JIS2K"))

    def package_info(self):
        # The shared library is JIS2K.so (Perl XS extension)
        self.cpp_info.libs = ["JIS2K"]
        self.cpp_info.libdirs = ["lib/auto/Encode/JIS2K"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
