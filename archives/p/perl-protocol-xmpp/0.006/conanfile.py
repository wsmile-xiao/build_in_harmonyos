#!/usr/bin/env python3
"""Conan recipe for perl-protocol-xmpp 0.006 (Protocol::XMPP).

Pure Perl module — XMPP/Jabber protocol API.
Build system: ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlProtocolXMPPConan(ConanFile):
    name = "perl-protocol-xmpp"
    version = "0.006"
    description = "XMPP/Jabber protocol API - Pure Perl module"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Protocol-XMPP"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Static linking config (pure Perl module, no binaries)
        from conan.tools.gnu import AutotoolsToolchain
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        # Apply patches if any (from conandata.yml)
        apply_conandata_patches(self)

        # Run perl Makefile.PL && make
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        # Copy Perl .pm and .pod files to lib/ at package root for G4 compatibility
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=os.path.dirname(target))

        # Also copy .pod files
        for pod_file in glob.glob(os.path.join(staging, "**", "*.pod"), recursive=True):
            rel = os.path.relpath(pod_file, staging)
            parts = rel.split(os.sep)
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pod_file), src=os.path.dirname(pod_file), dst=os.path.dirname(target))

    def package_info(self):
        # Pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers
        perl_site_lib = os.path.join(self.package_folder, "lib", "perl5", "site_perl", "5.42.0")
        self.runenv_info.append_path("PERL5LIB", perl_site_lib)
