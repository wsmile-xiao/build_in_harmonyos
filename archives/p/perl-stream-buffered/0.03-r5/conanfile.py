#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) module.
perl-stream-buffered 0.03-r5 — Stream::Buffered: temporary buffer to save bytes.
Pure Perl module, no C/C++ compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlStreamBufferedConan(ConanFile):
    name = "perl-stream-buffered"
    version = "0.03-r5"
    description = "Stream::Buffered - temporary buffer to save bytes (Pure Perl module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Stream-Buffered"
    url = ""

    # L0p: OHOS profile requires all four settings
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module using ExtUtils::MakeMaker
        self.run("perl Makefile.PL INSTALLDIRS=site", env="conanrun")
        self.run("make -j1", env="conanrun")

    def package(self):
        # Install to package folder using DESTDIR
        self.run('make install DESTDIR="{}"'.format(self.package_folder), env="conanrun")
        # Copy .pm files to standard lib/ for Conan artifact detection (G4)
        src_base = os.path.join(self.package_folder, "data", "service", "hnp", "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0")
        copy(self, "*.pm", src=src_base, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module - no C/C++ libraries
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib"))
