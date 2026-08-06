#!/usr/bin/env python3
"""Conan recipe for Devel-CheckCompiler 0.03 — pure Perl module.

Build system: Perl Module::Build (Build.PL), but Module::Build is not available
on OHOS. We create a Makefile.PL using ExtUtils::MakeMaker to replace Build.PL,
following the same pattern used by other Perl modules in this repository
(e.g. perl-proc-forksafe, perl-crypt-argon2).

The module is pure Perl — no XS, no compiled C code in the package itself.
It uses ExtUtils::CBuilder at runtime for optional C compiler checks.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DevelCheckCompilerConan(ConanFile):
    name = "devel-checkcompiler"
    version = "0.03"
    description = "Check the compiler's availability - detects C99 compiler support for Perl modules"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/Devel::CheckCompiler"
    url = ""  # CI fills this

    # Pure Perl module — settings present for profile compatibility
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)

        # Create Makefile.PL to replace Build.PL (Module::Build not available on OHOS)
        makefile_pl = """use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Devel::CheckCompiler',
    VERSION_FROM  => 'lib/Devel/CheckCompiler.pm',
    ABSTRACT_FROM => 'lib/Devel/CheckCompiler.pm',
    AUTHOR        => 'Tokuhiro Matsuno <tokuhirom AAJKLFJEF@ GMAIL COM>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'ExtUtils::CBuilder' => 0,
        'parent'             => 0,
        'Exporter'           => 0,
    },
    BUILD_REQUIRES => {
        'ExtUtils::CBuilder' => 0,
        'parent'             => 0,
    },
    test => {
        TESTS => 't/*.t',
    },
    INST_LIB  => 'blib/lib',
    INST_ARCHLIB => 'blib/arch',
);
"""
        with open(os.path.join(self.source_folder, "Makefile.PL"), "w") as f:
            f.write(makefile_pl)

        # Run perl Makefile.PL
        self.run("perl Makefile.PL INSTALLDIRS=site", env="conanrun")

        # Run make
        self.run("make -j1", env="conanrun")

    def package(self):
        # Copy the built .pm files from blib/lib to the package's lib/perl5 directory
        copy(self, "*.pm",
             src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # Pure Perl module — no compiled libraries
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        self.cpp_info.libdirs = ["lib", "lib/perl5"]
        self.cpp_info.libs = []
