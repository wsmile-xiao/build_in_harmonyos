#!/usr/bin/env python3
"""Conan recipe — Package::Variant (pure Perl module).

Build system: ExtUtils::MakeMaker (perl Makefile.PL)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlPackageVariantConan(ConanFile):
    name = "perl-package-variant"
    version = "1.003002-r4"
    description = "Package::Variant - Parameterizable packages for Perl"
    license = "Perl_5"
    homepage = "https://metacpan.org/dist/Package-Variant"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module — use MakeMaker with INSTALL_BASE
        self.run("perl Makefile.PL INSTALL_BASE=%s" % self.package_folder, cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install directly to package folder (INSTALL_BASE set in build)
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — MakeMaker INSTALL_BASE layout: lib/perl5/
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info("PERL5LIB += %s" % perl_lib)
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
