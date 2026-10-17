#!/usr/bin/env python3
"""Conan recipe — perl-orlite (ORLite) 2.00-r0

Pure Perl module: Extremely light weight SQLite-specific ORM.
Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlorliteConan(ConanFile):
    name = "perl-orlite"
    version = "2.00-r0"
    description = "Extremely light weight SQLite-specific ORM (ORLite)"
    license = "GPL-1.0-or-later or Artistic-1.0"
    homepage = "https://metacpan.org/dist/ORLite"
    url = ""  # CI fills this

    # R32: settings.os must include OHOS
    # L0p: OHOS profile requires all four settings
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Perl module deps (DBI, DBD::SQLite) managed by Perl, not Conan

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # E155: Perl ExtUtils::MakeMaker build
        self.run("perl Makefile.PL")
        self.run("make -j1")

    def package(self):
        # Copy built Perl module to a predictable package layout
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # Pure Perl module — no C libraries
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Expose Perl lib path via runenv (append_path so multiple
        # Perl module packages don't overwrite each other's PERL5LIB)
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
