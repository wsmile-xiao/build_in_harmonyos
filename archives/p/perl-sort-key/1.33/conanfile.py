#!/usr/bin/env python3
"""Conan recipe for perl-sort-key 1.33 (Perl XS module).

Build system: ExtUtils::MakeMaker (Makefile.PL)
Sort::Key - the fastest way to sort anything in Perl.
This is a Perl XS(C) module that compiles Key.xs into Key.so.

On HarmonyOS, CRT files (crti.o, crtn.o, crtbeginS.o, crtendS.o) are missing,
so -nostartfiles -nodefaultlibs -lc link flags are required (same as perl-dbd-pg).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlSortKeyConan(ConanFile):
    name = "perl-sort-key"
    version = "1.33"
    description = "Sort::Key - the fastest way to sort anything in Perl"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Sort-Key"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # Apply patch: adds -nostartfiles -nodefaultlibs -lc link flags
        # to bypass missing CRT files on HarmonyOS
        apply_conandata_patches(self)

        src = self.source_folder

        # Run perl Makefile PL
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=src)

        # Build
        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        # Use DESTDIR staging approach (standard Perl module packaging)
        tmpdir = os.path.join(self.build_folder, "staging")
        self.run(f"make install DESTDIR={tmpdir}", cwd=src)

        # Walk staging dir and copy all files to package_folder
        for root, _, files in os.walk(tmpdir):
            for f in files:
                src_file = os.path.join(root, f)
                rel = os.path.relpath(src_file, tmpdir)
                # Find 'lib' in path components to normalize install path
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
        # This is a Perl XS module (.so), not a standalone C library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
