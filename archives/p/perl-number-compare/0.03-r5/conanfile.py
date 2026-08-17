#!/usr/bin/env python3
"""Conan recipe — Perl module Number::Compare (pure Perl, no XS/C).

Build system: ExtUtils::MakeMaker (perl Makefile.PL + make).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlNumberCompareConan(ConanFile):
    name = "perl-number-compare"
    version = "0.03-r5"
    description = "Perl module for numeric comparisons"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Number-Compare"
    url = "https://metacpan.org/dist/Number-Compare"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        self.run("perl Makefile.PL INSTALL_BASE=", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install to package folder via DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"', env="conanbuild")
        # Also copy .pm files to a standard lib/ directory for package structure
        pm_files = glob.glob(os.path.join(self.package_folder, "**", "Compare.pm"), recursive=True)
        if not pm_files:
            raise Exception("Compare.pm not found after make install — package is incomplete")
        src_dir = os.path.dirname(pm_files[0])
        copy(self, "*.pm", src=src_dir, dst=os.path.join(self.package_folder, "lib", "Number"))

    def package_info(self):
        # Pure Perl module — no C libraries, headers, or binaries
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = []
        # Expose Perl module path via PERL5LIB for downstream consumers
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
