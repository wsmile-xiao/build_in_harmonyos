#!/usr/bin/env python3
"""Conan recipe — Crypt::CAST5 Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Perlcryptcast5Conan(ConanFile):
    name = "perl-crypt-cast5"
    version = "0.05-r14"
    description = "CAST5 block cipher for Perl (Crypt::CAST5)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Crypt-CAST5"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — only Perl core modules (Test::More)
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
        # Use cwd=self.source_folder because basic_layout may put build in a subfolder
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts to package folder in standard layout
        # .so goes to lib/auto/Crypt/CAST5/ (Perl auto path)
        # .pm goes to lib/Crypt/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "CAST5.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "CAST5"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "CAST5"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "CAST5"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "CAST5"))
        copy(self, "CAST5.pm",
             src=os.path.join(blib_lib, "Crypt"),
             dst=os.path.join(self.package_folder, "lib", "Crypt"))

    def package_info(self):
        # The shared library is CAST5.so (Perl XS extension)
        self.cpp_info.libs = ["CAST5"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/CAST5"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
