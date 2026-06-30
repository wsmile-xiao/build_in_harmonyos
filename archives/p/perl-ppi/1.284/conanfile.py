#!/usr/bin/env python3
"""Conan recipe — perl-ppi 1.284 (PPI - Parse, Analyze and Manipulate Perl)

Build system: ExtUtils::MakeMaker (Makefile.PL)
Category: Pure Perl module (no compiled binaries)
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlPpiConan(ConanFile):
    name = "perl-ppi"
    version = "1.284"
    description = "PPI - Parse, Analyze and Manipulate Perl (without perl)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/PPI"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Static linking config for terminal tools
        # PPI is a pure Perl module with no compiled binaries
        from conan.tools.gnu import AutotoolsToolchain
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        # Apply patches if any (from conandata.yml)
        apply_conandata_patches(self)
        # ExtUtils::MakeMaker build system: perl Makefile.PL && make
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        # Copy Perl .pm files to lib/ at package root for G4 compatibility
        # Find all .pm files in staging and copy preserving relative paths
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            # Find the site_perl part of the path
            rel = os.path.relpath(pm_file, staging)
            # Try to extract the path relative to site_perl
            parts = rel.split(os.sep)
            # Look for 'site_perl' in the path
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=os.path.dirname(target))

    def package_info(self):
        # PPI is a pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
