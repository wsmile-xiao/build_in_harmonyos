#!/usr/bin/env python3
"""Conan recipe — Statistics::ChiSquare (pure Perl module).

Statistics::ChiSquare calculates how well-distributed is your data.
This is a pure Perl module built with ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlstatisticschisquareConan(ConanFile):
    name = "perl-statistics-chisquare"
    version = "1.0000-r2"
    description = "How well-distributed is your data? (pure Perl chi-square statistics module)"
    license = "GPL-2.0-only OR Artistic-1.0"
    homepage = "https://github.com/DrHyde/perl-modules-Statistics-ChiSquare"
    url = ""  # CI fills this

    # Pure Perl module — no compiler/build_type needed, but CI L0p requires all four
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find the installed .pm file and copy to lib/ in package folder
        pm_files = glob.glob(os.path.join(dest_dir, "**", "Statistics", "ChiSquare.pm"), recursive=True)
        if pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "Statistics")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_files[0], target_dir)
        else:
            raise Exception("Statistics/ChiSquare.pm not found in DESTDIR after make install")

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
