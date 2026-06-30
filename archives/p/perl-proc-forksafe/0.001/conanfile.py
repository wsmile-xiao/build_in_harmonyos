#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) module.
perl-proc-forksafe 0.001 — Proc::ForkSafe: help make objects fork safe.
Pure Perl module, no C/C++ compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlProcForksafeConan(ConanFile):
    name = "perl-proc-forksafe"
    version = "0.001"
    description = "Proc::ForkSafe - help make objects fork safe"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://github.com/skaji/perl-Proc-ForkSafe"
    url = ""

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

        # Create Makefile.PL since the source tarball doesn't include one
        # (original distribution uses Dist::Zilla / Module::Build::Tiny)
        makefile_pl = '''use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Proc::ForkSafe',
    VERSION_FROM  => 'lib/Proc/ForkSafe.pm',
    ABSTRACT_FROM => 'lib/Proc/ForkSafe.pm',
    AUTHOR        => 'Shoichi Kaji <skaji@cpan.org>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'perl' => '5.008001',
    },
    TEST_REQUIRES => {
        'Test::More' => 0,
    },
);
'''
        with open(os.path.join(self.source_folder, "Makefile.PL"), "w") as f:
            f.write(makefile_pl)

        # Run perl Makefile.PL
        self.run("perl Makefile.PL INSTALLDIRS=site", env="conanrun")

        # Run make
        self.run("make -j1", env="conanrun")

    def package(self):
        # Copy the built .pm files from blib/lib to the package's lib/ directory
        # blib/lib/Proc/ForkSafe.pm -> lib/Proc/ForkSafe.pm
        copy(self, "*.pm",
             src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module, no compiled libraries
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
