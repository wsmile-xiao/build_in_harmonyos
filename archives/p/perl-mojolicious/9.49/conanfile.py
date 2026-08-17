#!/usr/bin/env python3
"""Conan recipe for perl-mojolicious 9.49 — Mojolicious web framework.

Pure Perl distribution, Makefile.PL (ExtUtils::MakeMaker) build. Deps are
perl core modules (IO::Socket::IP, Sub::Util) — no extra conan requires
beyond perl/5.42.2 (published to ohpcd). Installs into site_perl.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlMojoliciousConan(ConanFile):
    name = "perl-mojolicious"
    version = "9.49"
    description = "Mojolicious — real-time web application framework (Perl)"
    license = "Artistic-2.0"
    homepage = "https://mojolicious.org/"
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
        perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        self.run(
            f'{perl} Makefile.PL INSTALLDIRS=site '
            f'PREFIX={self.package_folder}',
            cwd=self.source_folder,
        )
        self.run("make -j1", cwd=self.source_folder)
        self.run("make install", cwd=self.source_folder)

    def package(self):
        site = os.path.join(self.package_folder, "lib", "perl5", "site_perl")
        mojo = os.path.join(site, "Mojolicious.pm")
        if not os.path.isfile(mojo):
            raise ConanException(f"Mojolicious.pm not installed: {mojo}")

    def package_info(self):
        self.output.info("PERL5LIB=%s/lib/perl5/site_perl" % self.package_folder)
