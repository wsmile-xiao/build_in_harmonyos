#!/usr/bin/env python3
"""Conan recipe for perl-role-basic 0.16 (Role::Basic).

A lightweight role implementation for Perl, an alternative to Moose::Role.
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRoleBasicConan(ConanFile):
    name = "perl-role-basic"
    version = "0.16"
    description = "Lightweight role (Role::Basic) implementation for Perl, Moose::Role alternative"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Role-Basic"
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
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.source_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        dst = os.path.join(self.package_folder, "lib", "perl5")
        os.makedirs(dst, exist_ok=True)

        # Find all .pm and .pod files in staging and preserve Role/ subdirectory structure
        for pm in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm, staging)
            # Find the "Role/" prefix in the relative path
            parts = rel.split(os.sep)
            role_idx = None
            for i, part in enumerate(parts):
                if part == "Role":
                    role_idx = i
                    break
            if role_idx is not None:
                # Preserve from Role/ onwards
                rel_from_role = os.path.join(*parts[role_idx:])
                target = os.path.join(dst, rel_from_role)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(pm, target)

        # Also copy .pod files
        for pod in glob.glob(os.path.join(staging, "**", "*.pod"), recursive=True):
            rel = os.path.relpath(pod, staging)
            parts = rel.split(os.sep)
            role_idx = None
            for i, part in enumerate(parts):
                if part == "Role":
                    role_idx = i
                    break
            if role_idx is not None:
                rel_from_role = os.path.join(*parts[role_idx:])
                target = os.path.join(dst, rel_from_role)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(pod, target)

    def package_info(self):
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
