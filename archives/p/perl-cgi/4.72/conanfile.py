#!/usr/bin/env python3
"""Conan recipe for perl-cgi 4.72 — CGI module
(pure-Perl, CPAN source, zero runtime dependencies).

Pure-Perl module: build via perl Makefile.PL → make → make install
DESTDIR into the conan package folder; consumers add site/lib to PERL5LIB.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlCgiConan(ConanFile):
    name = "perl-cgi"
    version = "4.72"
    description = "CGI — Handle Common Gateway Interface requests and responses"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/CGI"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # CGI.pm line 4 requires URI (runtime dep — CI hnp perl lacks it)
        self.requires("perl-uri/5.35")

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
        # locate CGI.pm (site_perl or lib/perl5 — walk to avoid drift)
        found = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "CGI.pm" in files:
                found = root
                break
        if not found:
            raise ConanException("CGI.pm not found in package")

    def package_info(self):
        # expose the perl5 dir containing CGI.pm as PERL5LIB
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "CGI.pm" in files:
                site = root
                break
        if site:
            self.output.info(f"PERL5LIB={site}")
