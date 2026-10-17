#!/usr/bin/env python3
"""Conan recipe for extutils-depends — pure Perl module (Makefile.PL).

Build system: perl Makefile.PL + make + make install
No compiled code — pure Perl, no XS, no C dependencies.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ExtUtilsDependsConan(ConanFile):
    name = "extutils-depends"
    version = "0.8002"
    description = "Easily build XS extensions that depend on XS extensions"
    license = "LGPL-2.1"
    homepage = "https://metacpan.org/pod/ExtUtils::Depends"
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
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL PREFIX=/usr/local", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        self.run(f'make install DESTDIR="{self.package_folder}"', cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Expose Perl module path via PERL5LIB so consumers can use the module
        pm_files = glob.glob(os.path.join(self.package_folder, "**", "ExtUtils", "Depends.pm"), recursive=True)
        if pm_files:
            perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
            self.runenv_info.append_path("PERL5LIB", perl_lib_dir)
