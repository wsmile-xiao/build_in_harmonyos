#!/usr/bin/env python3
"""Conan recipe — perl-string-random 0.32-r2 (pure Perl module).

String::Random — generate random strings based on a pattern.
Uses ExtUtils::MakeMaker (Makefile.PL) build system.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlStringRandomConan(ConanFile):
    name = "perl-string-random"
    version = "0.32-r2"
    description = "Perl module to generate random strings based on a pattern"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/release/String-Random"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module; runtime deps (Carp, Exporter, parent) are
        # provided by the Perl interpreter itself.
        pass

    def layout(self):
        # Use simple layout — no build_folder helpers needed
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply any declared patches (none currently, but required by G1)
        apply_conandata_patches(self)
        # Create a Makefile.PL since upstream uses Build.PL (Module::Build)
        # but the OHOS Perl installation only has ExtUtils::MakeMaker.
        makefile_pl = """use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME         => 'String::Random',
    VERSION_FROM => 'lib/String/Random.pm',
    LICENSE      => 'perl',
    PREREQ_PM    => {
        'Carp'     => 0,
        'Exporter' => 0,
        'parent'   => 0,
    },
    TEST_REQUIRES => {
        'Test::More' => 0.88,
    },
);
"""
        with open("Makefile.PL", "w") as f:
            f.write(makefile_pl)

        self.run("perl Makefile.PL")
        self.run("make -j1")

    def package(self):
        # Install to the package root using DESTDIR
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        # Set include dirs empty — this is a Perl module
        self.cpp_info.includedirs = []
