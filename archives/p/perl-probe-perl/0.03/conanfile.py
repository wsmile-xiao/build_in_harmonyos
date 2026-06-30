#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) module.
perl-probe-perl 0.03 — Probe::Perl: Information about the currently running perl.
Pure Perl module, no C/C++ compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlProbePerlConan(ConanFile):
    name = "perl-probe-perl"
    version = "0.03"
    description = "Probe::Perl - Information about the currently running perl"
    license = "perl_5"
    homepage = "https://metacpan.org/release/Probe-Perl"
    url = ""

    # Pure Perl module — only os and arch matter
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Pure Perl module using ExtUtils::MakeMaker
        self.run("perl Makefile.PL INSTALLDIRS=site", env="conanrun")
        self.run("make -j1", env="conanrun")

    def package(self):
        # Install to package folder using DESTDIR
        self.run('make install DESTDIR="{}"'.format(self.package_folder), env="conanrun")
        # Also copy .pm files to standard lib/ for Conan artifact detection (G4)
        # Perl modules are installed under nested site_perl paths; copy to lib/Probe/
        src_base = os.path.join(self.package_folder, "data", "service", "hnp", "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0")
        copy(self, "*.pm", src=src_base, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module - no C/C++ libraries
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
