#!/usr/bin/env python3
"""Conan recipe for perl-parallel-pipes (Parallel::Pipes) — pure Perl module.

Parallel::Pipes provides parallel processing using pipe(2) for communication
and synchronization. This is a pure Perl module.

Build system: ExtUtils::MakeMaker (Makefile.PL) — fallback for Module::Build::Tiny
which is not available on the CI worker.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlparallelpipesConan(ConanFile):
    name = "perl-parallel-pipes"
    version = "0.201"
    description = "Parallel processing using pipe(2) for communication and synchronization"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://github.com/skaji/Parallel-Pipes"
    url = ""  # CI fills this

    # Pure Perl module — settings present for profile compatibility (L0p)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Pure Perl module — no C/C++ layout needed
        # Using pass instead of basic_layout to avoid 'build' directory
        # conflicting with Module::Build::Tiny's 'Build' script on
        # case-insensitive filesystems
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (none for this module)
        apply_conandata_patches(self)

        # Create Makefile.PL using ExtUtils::MakeMaker (Perl core module)
        # Source uses Module::Build::Tiny (Build.PL) which is not available on CI worker
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            makefile_pl_content = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Parallel::Pipes',
    VERSION_FROM  => 'lib/Parallel/Pipes.pm',
    ABSTRACT_FROM => 'lib/Parallel/Pipes.pm',
    AUTHOR        => 'Shoichi Kaji <skaji@cpan.org>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'perl' => '5.008001',
    },
    NO_MYMETA => 1,
);
"""
            with open(makefile_pl, "w") as f:
                f.write(makefile_pl_content)

        # Run perl Makefile.PL && make
        self.run("perl Makefile.PL INSTALLDIRS=site")
        self.run("make")

    def package(self):
        # Copy .pm files from blib/lib to package lib/
        blib_lib = os.path.join(self.build_folder, "blib", "lib")
        if not os.path.isdir(blib_lib):
            raise Exception("blib/lib not found — build may have failed")
        copy(self, "*.pm", src=blib_lib, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C/C++ libraries to link
        # R26 note: static linking not applicable (no native binaries)
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the Perl module
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.runenv_info.define_path("PERL5LIB", lib_dir)
