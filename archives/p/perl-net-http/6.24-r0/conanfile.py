#!/usr/bin/env python3
"""Conan recipe — Perl module Net::HTTP 6.24.

Pure Perl module using ExtUtils::MakeMaker (perl Makefile.PL).
No binary artifacts; no static linking needed (R26 N/A for pure Perl).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnethttpConan(ConanFile):
    name = "perl-net-http"
    version = "6.24-r0"
    description = "Low-level HTTP connection (client)"
    license = "MIT"
    homepage = "https://metacpan.org/release/Net-HTTP"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl module build: perl Makefile.PL && make
        self.run("perl Makefile.PL")
        self.run("make")

    def package(self):
        # Copy Perl module files to lib/ for Conan artifact detection
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no libraries to link
        self.cpp_info.libs = []
