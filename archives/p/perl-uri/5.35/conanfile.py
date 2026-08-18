#!/usr/bin/env python3
"""Conan recipe for perl-uri 5.35 — URI module
(pure-Perl, CPAN source, zero runtime dependencies).

Pure-Perl module: build via perl Makefile.PL → make → make install
DESTDIR into the conan package folder; consumers add site/lib to PERL5LIB.
NOTE: make install paths carry the full perl prefix
(/storage/Users/currentUser/usr/local/lib/perl5/5.42.2).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlUriConan(ConanFile):
    name = "perl-uri"
    version = "5.35"
    description = "URI — Uniform Resource Identifiers (absolute and relative)"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/URI"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        perl = "/data/service/hnp/bin/perl"
        self.run(f'{perl} Makefile.PL', cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        staging = os.path.join(self.build_folder, "perl-stage")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "perl-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"perl staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        # locate URI.pm (install prefix varies by perl build — walk)
        found = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "URI.pm" in files:
                found = root
                break
        if not found:
            raise ConanException("URI.pm not found in package")

    def package_info(self):
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "URI.pm" in files:
                site = root
                break
        if site:
            self.output.info(f"PERL5LIB={site}")
