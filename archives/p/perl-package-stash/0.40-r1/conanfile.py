#!/usr/bin/env python3
"""Conan recipe for perl-package-stash 0.40-r1 (Package::Stash CPAN module).

This is a pure-Perl module built with ExtUtils::MakeMaker (Makefile.PL).
Build steps: perl Makefile.PL -> make -> make install

Platform note: XS variant (Package::Stash::XS) .so loading may be restricted
by SELinux on OHOS; the pure-perl (PP) implementation is fully functional.
E190: sys/types.h not found during XS compiler check is non-fatal for PP modules.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlPackageStashConan(ConanFile):
    name = "perl-package-stash"
    version = "0.40-r1"
    description = "Routines for manipulating stashes (Package::Stash CPAN module)"
    license = "perl"
    homepage = "https://metacpan.org/dist/Package-Stash"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        # Set INSTALL_BASE at Makefile.PL time so install targets use it
        # PUREPERL_ONLY=1 forces pure-perl implementation (no XS)
        self.run("perl Makefile.PL --pureperl-only INSTALL_BASE={}".format(self.package_folder))
        self.run("make PUREPERL_ONLY=1")

    def package(self):
        # Install using the INSTALL_BASE set during Makefile.PL
        self.run("make install PUREPERL_ONLY=1")

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Perl module: expose lib path for consumers
        perl5_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.prepend_path("PERL5LIB", perl5_lib)
