#!/usr/bin/env python3
"""Conan recipe — perl-sql-statement 1.414-r1 (SQL::Statement pure Perl module).

Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install)
This is a pure Perl module — no C compilation, no .so/.a libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlsqlstatementConan(ConanFile):
    name = "perl-sql-statement"
    version = "1.414-r1"
    description = "SQL parsing and processing engine (SQL::Statement pure Perl module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/SQL-Statement"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module build: perl Makefile.PL && make
        self.run(f"cd {self.source_folder} && perl Makefile.PL")
        self.run(f"cd {self.source_folder} && make -j1")

    def package(self):
        # Install Perl modules via make install with DESTDIR
        dest = self.package_folder
        self.run(f"cd {self.source_folder} && make install DESTDIR={dest}")

    def package_info(self):
        # Pure Perl module — no compiled libraries to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # Set PERL5LIB so consumers can find the installed Perl modules
        perl_lib = os.path.join(self.package_folder, "data", "service", "hnp", "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        # HMDFS restricts .so loading from user dirs; Params::Util (XS dep) needs PP mode
        self.runenv_info.define("PERL_PARAMS_UTIL_PP", "1")
