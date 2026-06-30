#!/usr/bin/env python3
"""Conan recipe for perl-protocol-http2 1.11 (Protocol::HTTP2).

Pure Perl module - HTTP/2 protocol implementation (RFC 7540).
Build system: ExtUtils::MakeMaker (Makefile.PL) — fallback for Module::Build::Tiny.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlProtocolHTTP2Conan(ConanFile):
    name = "perl-protocol-http2"
    version = "1.11"
    description = "HTTP/2 protocol implementation (RFC 7540) - Pure Perl module"
    license = "perl_5"
    homepage = "https://github.com/vlet/p5-Protocol-HTTP2"
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

        # Original source uses Module::Build::Tiny (Build.PL), which is not
        # available on the platform. Create a standard Makefile.PL using
        # ExtUtils::MakeMaker as a fallback.
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            makefile_pl_content = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Protocol::HTTP2',
    VERSION_FROM  => 'lib/Protocol/HTTP2.pm',
    ABSTRACT_FROM => 'lib/Protocol/HTTP2.pm',
    AUTHOR        => 'Vladimir Lettiev <thecrux@gmail.com>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'MIME::Base64' => '3.11',
        'Scalar::Util' => 0,
    },
    TEST_REQUIRES => {
        'Test::More' => '0.98',
    },
    MIN_PERL_VERSION => '5.008001',
    NO_MYMETA => 1,
);
"""
            with open(makefile_pl, "w") as f:
                f.write(makefile_pl_content)

        # Run perl Makefile.PL && make
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        # Copy Perl .pm files to lib/ at package root for G4 compatibility
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

    def package_info(self):
        # Pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers
        perl_site_lib = os.path.join(self.package_folder, "lib", "perl5", "site_perl", "5.42.0")
        self.runenv_info.append_path("PERL5LIB", perl_site_lib)
