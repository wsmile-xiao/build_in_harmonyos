#!/usr/bin/env python3
"""Conan recipe — Spiffy (perl-spiffy) 0.46

Spiffy Perl Interface Framework For You — pure-Perl module.
Build system: ExtUtils::MakeMaker (perl Makefile.PL + make).

References:
  - R1: parameter minimalism — only INSTALL_BASE
  - R27: dependencies use @ohpcd/stable (none for this module)
  - R28: test_package/ present
  - R32: settings.os check uses in ("Linux", "OHOS")
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlSpiffyConan(ConanFile):
    name = "perl-spiffy"
    version = "0.46"
    description = "Spiffy Perl Interface Framework For You — pure-Perl module"
    license = "perl"
    homepage = "https://metacpan.org/dist/Spiffy"
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
        # Pure-Perl module: ExtUtils::MakeMaker
        # INSTALL_BASE=/ makes files install to $DESTDIR/lib/perl5/
        self.run("perl Makefile.PL INSTALL_BASE=/")
        # R32: HarmonyOS compatible
        self.run("make -j1")

    def package(self):
        # Install to staging directory with DESTDIR
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"make install DESTDIR={staging}")
        # Copy lib/ subtree to package folder
        src_lib = os.path.join(staging, "lib")
        if not os.path.exists(src_lib):
            raise Exception(f"Package staging lib directory not found: {src_lib}")
        copy(self, "*", src_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure-Perl module: no C libraries to link against
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the module
        perl_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "perl5", "*")
        )
        for perl_dir in perl_dirs:
            if os.path.isdir(perl_dir):
                self.runenv_info.append_path("PERL5LIB", perl_dir)
        # Also add lib/perl5 base for pure-Perl modules
        base_perl = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            self.runenv_info.append_path("PERL5LIB", base_perl)
