#!/usr/bin/env python3
"""Conan recipe — Perl XS module (ExtUtils::MakeMaker / Makefile.PL).

Proc::Wait3 - Perl extension for wait3 system call (XS/C module).
Build system: perl Makefile PL (ExtUtils::MakeMaker).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

class PerlProcWait3Conan(ConanFile):
    name = "perl-proc-wait3"
    version = "0.05"
    description = "Perl extension for wait3 system call (XS/C module)"
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Proc::Wait3"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL INSTALLDIRS=site")
        self.run("make -j1")

    def package(self):
        # Install directly to package folder using DESTDIR
        self.run('make install DESTDIR="{}"'.format(self.package_folder))
        # Also copy .pm and .so to standard lib/ for Conan artifact detection (G4)
        # Perl XS modules install under nested site_perl paths; copy to lib/ for detection
        src_base = os.path.join(
            self.package_folder, "data", "service", "hnp", "perl.org",
            "perl_5.42.0", "lib", "site_perl", "5.42.0", "aarch64-linux"
        )
        copy(self, "*.pm", src=src_base, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.so", src=os.path.join(src_base, "auto"), dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
