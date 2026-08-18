#!/usr/bin/env python3
"""Conan recipe — perl-number-misc (Number::Misc) 1.2

Pure Perl module: handy utilities for numbers.
Build system: perl Makefile.PL + make + make install
No C/XS compilation, no external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnumbermiscConan(ConanFile):
    name = "perl-number-misc"
    version = "1.2"
    description = "Number::Misc - handy utilities for numbers"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Number-Misc"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module — no external dependencies.
        # Requires Perl 5.003+ only (core Perl).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl: perl Makefile.PL && make
        # Set INSTALL_BASE to a build-local dir for controlled packaging
        install_base = os.path.join(self.build_folder, "_perl_install")
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')
        self.run("make -j1")

    def package(self):
        # Install to the build-local INSTALL_BASE, then copy to standard dirs
        install_base = os.path.join(self.build_folder, "_perl_install")
        self.run(f'make install')
        # With INSTALL_BASE, modules go to lib/perl5/
        src_lib = os.path.join(install_base, "lib", "perl5")
        if os.path.exists(src_lib):
            copy(self, "*.pm", src_lib, os.path.join(self.package_folder, "lib"))
            copy(self, "*.pod", src_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Perl modules are in lib/ — set PERL5LIB for consumers
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
