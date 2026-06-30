#!/usr/bin/env python3
"""Conan recipe — Perl pure module (perl Makefile.PL + make).

This is a pure Perl module (Net::NTP) that decodes NTP server responses.
No C/XS compilation is involved — only .pm file installation.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetntpConan(ConanFile):
    name = "perl-net-ntp"
    version = "1.5-r1"
    description = "Perl extension for decoding NTP server responses (Net::NTP)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-NTP"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module; Time::HiRes is a core Perl module
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        self.run("perl Makefile.PL")
        self.run("make")

    def package(self):
        # Install via make install to staging (DESTDIR mode)
        self.run("make install DESTDIR={}".format(self.package_folder))
        # Also copy .pm files to standard lib/ for Conan product detection (G4)
        pm_files = glob.glob(os.path.join(self.package_folder, "**", "*.pm"), recursive=True)
        for pm in pm_files:
            # Preserve relative path from blib/lib or lib
            rel = os.path.relpath(pm, self.package_folder)
            # Find the "Net" or similar module-level directory
            parts = rel.split(os.sep)
            # Try to find "Net" in the path and reconstruct from there
            if "Net" in parts:
                idx = parts.index("Net")
                rel_from_net = os.path.join(*parts[idx:])
                dst = os.path.join(self.package_folder, "lib", rel_from_net)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                copy(self, os.path.basename(pm), os.path.dirname(pm), os.path.dirname(dst))

    def package_info(self):
        # Pure Perl module — no C library to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
