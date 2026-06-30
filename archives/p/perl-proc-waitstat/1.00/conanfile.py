#!/usr/bin/env python3
"""Conan recipe — Perl module Proc::WaitStat (ExtUtils::MakeMaker).

Build system: perl Makefile.PL INSTALLDIRS=site && make && make install
This is a pure Perl module (no XS/C), depends on IPC::Signal.
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlProcWaitstatConan(ConanFile):
    name = "perl-proc-waitstat"
    version = "1.00"
    description = "Proc::WaitStat - Interpret and act on wait() status values"
    license = "perl_5"
    homepage = "https://metacpan.org/release/Proc-WaitStat"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    exports = "lib/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Pure Perl module — no C compilation, no static linking needed
        pass

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # DESTDIR staging approach (standard Perl module packaging)
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        # Walk staging dir and copy all files to package_folder
        # Normalize install path to start at lib/
        for root, _, files in os.walk(staging):
            for f in files:
                src_file = os.path.join(root, f)
                rel = os.path.relpath(src_file, staging)
                parts = rel.split(os.sep)
                lib_idx = -1
                for i, p in enumerate(parts):
                    if p == 'lib':
                        lib_idx = i
                        break
                if lib_idx >= 0:
                    dst_rel = os.path.join(*parts[lib_idx:])
                else:
                    dst_rel = os.path.join("lib", rel)
                dst = os.path.join(self.package_folder, dst_rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src_file, dst)

    def package_info(self):
        # Pure Perl module — .pm files only, no C libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/perl5"]
