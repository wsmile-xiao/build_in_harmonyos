#!/usr/bin/env python3
"""Conan recipe — Net::DNS::Resolver::Programmable (pure Perl module).

Build system: ExtUtils::MakeMaker (perl Makefile.PL + make)
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetdnsresolverprogrammableConan(ConanFile):
    name = "perl-net-dns-resolver-programmable"
    version = "0.009-r4"
    description = "programmable DNS resolver class for offline emulation of DNS"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Net-DNS-Resolver-Programmable"
    url = ""  # CI fills this

    # Pure Perl module — minimal settings
    settings = "os"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl module build: perl Makefile.PL + make
        self.run("perl Makefile.PL")
        self.run("make")

    def package(self):
        # Install to staging directory using DESTDIR
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"make install DESTDIR={staging}")
        # Copy .pm files into lib/ in the package
        # Find all .pm files under staging and copy them preserving relative path
        for root, dirs, files in os.walk(staging):
            for f in files:
                if f.endswith(".pm"):
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, staging)
                    # Extract the path after the prefix (e.g., lib/site_perl/.../Net/...)
                    # Find 'lib' in the path and take everything from there
                    parts = rel.split(os.sep)
                    try:
                        idx = parts.index("lib")
                        rel_lib = os.path.join(*parts[idx:])
                    except ValueError:
                        rel_lib = rel
                    dst = os.path.join(self.package_folder, rel_lib)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
