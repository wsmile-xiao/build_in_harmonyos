#!/usr/bin/env python3
"""Conan recipe — perl-regexp-ipv6 (Regexp::IPv6) 0.03.

Pure Perl module using ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRegexpIPv6Conan(ConanFile):
    name = "perl-regexp-ipv6"
    version = "0.03"
    description = "Regular expression for IPv6 addresses (Regexp::IPv6)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Regexp-IPv6"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Perl EUMM build: run in source folder
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # make install with DESTDIR staging
        staging = self.package_folder + "_install"
        self.run(f'make install DESTDIR={staging}', cwd=self.source_folder)
        # Copy the .pm file to the package lib/perl5 directory
        dest = os.path.join(self.package_folder, "lib", "perl5", "Regexp")
        os.makedirs(dest, exist_ok=True)
        # Try to find the installed .pm file
        found = False
        if os.path.isdir(staging):
            for root, dirs, files in os.walk(staging):
                for f in files:
                    if f == "IPv6.pm":
                        shutil.copy2(os.path.join(root, f), os.path.join(dest, "IPv6.pm"))
                        found = True
                        break
                if found:
                    break
        # Fallback: copy from blib
        if not found:
            blib_pm = os.path.join(self.source_folder, "blib", "lib", "Regexp", "IPv6.pm")
            if os.path.exists(blib_pm):
                shutil.copy2(blib_pm, os.path.join(dest, "IPv6.pm"))
                found = True

    def package_info(self):
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
