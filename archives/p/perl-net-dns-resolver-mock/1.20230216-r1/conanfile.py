#!/usr/bin/env python3
"""Conan recipe — Perl module Net::DNS::Resolver::Mock.

Pure Perl module using Makefile.PL (ExtUtils::MakeMaker) build system.
No C compilation, no shared libraries, no static linking needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetdnsresolvermockConan(ConanFile):
    name = "perl-net-dns-resolver-mock"
    version = "1.20230216-r1"
    description = "Mock a DNS Resolver object for testing"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Net-DNS-Resolver-Mock"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl module build: Makefile.PL -> make
        self.run("perl Makefile.PL INSTALL_BASE=/usr/local", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install into package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)
        # Also copy .pm files to lib/ for standard Conan artifact discovery (G4)
        copy(self, "*.pm", os.path.join(self.source_folder, "blib", "lib"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # Expose Perl lib path for consumers via environment
        # Use append to preserve existing PERL5LIB (system Perl modules)
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append("PERL5LIB", perl_lib)
        self.buildenv_info.append("PERL5LIB", perl_lib)
