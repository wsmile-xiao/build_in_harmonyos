#!/usr/bin/env python3
"""Conan recipe for perl-strictures 2.000006-r4 (pure Perl module).

Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install)
This is a pure Perl module — no C/XS compilation, no shared libraries.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlstricturesConan(ConanFile):
    name = "perl-strictures"
    version = "2.000006-r4"
    description = "Turn on strict and make most warnings fatal (Perl module)"
    license = "GPL-1.0-or-later OR Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/strictures"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make && make test
        # Run in source_folder since Makefile.PL is there
        self.run("perl Makefile.PL", cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # Run upstream tests (make test / make check)
        self.run("make test", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Install to a staging dir
        dest = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{dest}"', cwd=self.source_folder, env="conanbuild")
        # Find the site_perl directory where .pm files were installed
        # and copy them flat into lib/
        pm_files = glob.glob(os.path.join(dest, "**", "*.pm"), recursive=True)
        for pm_file in pm_files:
            # Get path relative to the site_perl/<version>/ directory
            rel = os.path.relpath(pm_file, dest)
            # Strip everything up to and including site_perl/<version>/
            parts = rel.replace("\\", "/").split("/")
            if "site_perl" in parts:
                idx = parts.index("site_perl")
                # Skip site_perl and the version dir after it
                rel = "/".join(parts[idx + 2:])
            target_dir = os.path.join(self.package_folder, "lib", os.path.dirname(rel))
            os.makedirs(target_dir, exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=target_dir)

    def package_info(self):
        # Pure Perl module: no C/C++ libraries to link
        self.cpp_info.libs = []
