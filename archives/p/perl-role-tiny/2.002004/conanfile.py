#!/usr/bin/env python3
"""Conan recipe for Role::Tiny 2.002004 — Perl EUMM (ExtUtils::MakeMaker).

Pure Perl module providing Roles (a nouvelle cuisine portion size slice of Moose).
Build: perl Makefile.PL INSTALLDIRS=site && make && make install DESTDIR=...
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRoleTinyConan(ConanFile):
    name = "perl-role-tiny"
    version = "2.002004"
    description = "Roles: a nouvelle cuisine portion size slice of Moose"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Role-Tiny"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        destdir = os.path.join(src, "dest")
        self.run(f"make install DESTDIR={destdir}", cwd=src)

        # Find all .pm files under destdir and copy to lib/perl5/
        # preserving the Role/ subdirectory structure
        perl5lib = os.path.join(self.package_folder, "lib", "perl5")
        os.makedirs(perl5lib, exist_ok=True)

        for pm_file in glob.glob(
            os.path.join(destdir, "**", "*.pm"), recursive=True
        ):
            # Extract relative path starting from "Role/"
            rel = os.path.relpath(pm_file, destdir)
            idx = rel.find("Role/")
            if idx >= 0:
                rel = rel[idx:]
                dst_file = os.path.join(perl5lib, rel)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(pm_file, dst_file)
                self.output.info(f"Packaged: {rel}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
