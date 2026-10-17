#!/usr/bin/env python3
"""Conan recipe — perl-starlet 0.31-r3 (pure Perl module).

Starlet is a high-performance PSGI/Plack HTTP server.
This is a pure Perl module using Module::Install (Makefile.PL).
No C compiler needed.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlStarletConan(ConanFile):
    name = "perl-starlet"
    version = "0.31-r3"
    description = "Starlet - a simple, high-performance PSGI/Plack HTTP server"
    license = "Artistic-1.0 OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Starlet"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (none for this pure Perl module)
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        # Note: -I. needed because Perl 5.26+ removed '.' from @INC
        self.run("perl -I. Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to packaging root
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        # Pure Perl module — no C libraries
        # The installed files are .pm Perl modules under site_perl/
        self.cpp_info.libs = []
