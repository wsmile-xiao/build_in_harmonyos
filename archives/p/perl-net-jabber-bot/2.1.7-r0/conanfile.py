#!/usr/bin/env python3
"""Conan recipe — perl-net-jabber-bot 2.1.7-r0 (Pure Perl module)

Build system: perl Makefile.PL (ExtUtils::MakeMaker)
This is a pure Perl module with no compiled C extensions.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetjabberbotConan(ConanFile):
    name = "perl-net-jabber-bot"
    version = "2.1.7-r0"
    description = "Automated Jabber Bot creation - Pure Perl module"
    license = "perl"
    homepage = "https://metacpan.org/dist/Net-Jabber-Bot"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Static linking for terminal tools (no-op for pure Perl module)
        pass

    def build(self):
        # Apply patches if any (R3)
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install to staging directory
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)
        # Also copy .pm files to standard lib/ for product visibility (G4)
        src_perl = os.path.join(
            self.package_folder,
            "data", "service", "hnp", "perl.org", "perl_5.42.0",
            "lib", "site_perl", "5.42.0"
        )
        if os.path.isdir(src_perl):
            copy(self, "*.pm", src_perl, os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Set libdirs to the perl5 directory for visibility
        self.cpp_info.libdirs = ["lib/perl5"]
