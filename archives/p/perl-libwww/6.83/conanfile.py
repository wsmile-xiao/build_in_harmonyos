#!/usr/bin/env python3
"""Conan recipe for perl-libwww 6.83 — LWP (libwww-perl) HTTP client modules.

Pure Perl distribution, Makefile.PL (ExtUtils::MakeMaker) build. Installs
the libwww-perl modules into site_perl; consumers add site_perl to
PERL5LIB. Requires the perl/5.42.2 interpreter (published to ohpcd).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlLibwwwConan(ConanFile):
    name = "perl-libwww"
    version = "6.83"
    description = "libwww-perl — LWP HTTP client library (LWP::UserAgent etc.)"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/libwww-perl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "unknown"

    requires = "perl/5.42.2"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Pure Perl build: Makefile.PL -> make -> make install into site_perl.
        # INSTALLDIRS=site keeps modules under perl's site_perl tree.
        perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        self.run(
            f'{perl} Makefile.PL INSTALLDIRS=site '
            f'PREFIX={self.package_folder}',
            cwd=self.source_folder,
        )
        self.run("make -j1", cwd=self.source_folder)
        self.run("make install", cwd=self.source_folder)

    def package(self):
        # Verify LWP::UserAgent module installed
        site = os.path.join(
            self.package_folder, "lib", "perl5", "site_perl")
        ua = os.path.join(site, "LWP", "UserAgent.pm")
        if not os.path.isfile(ua):
            raise ConanException(f"LWP::UserAgent not installed: {ua}")

    def package_info(self):
        # Consumers set PERL5LIB to the site_perl dir at runtime
        self.output.info("PERL5LIB=%s/lib/perl5/site_perl" % self.package_folder)
