#!/usr/bin/env python3
"""Conan recipe for perl-params-validationcompiler — pure Perl module (Makefile.PL).

Build system: perl Makefile.PL + make + make install
No compiled code — pure Perl, no XS, no C dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlparamsvalidationcompilerConan(ConanFile):
    name = "perl-params-validationcompiler"
    version = "0.31"
    description = "Build an optimized subroutine parameter validator once, use it forever"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/dist/Params-ValidationCompiler"
    url = ""  # CI fills this

    # Pure Perl module — settings present for profile compatibility
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
        # Apply patches if any (none for this pure Perl module)
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        # INSTALL_BASE ensures installation goes to the expected location
        self.run("perl Makefile.PL INSTALL_BASE=/usr/local", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
