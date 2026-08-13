#!/usr/bin/env python3
"""Conan recipe for perl-string-shellquote 1.04-r5 (pure Perl module).

This module provides String::ShellQuote for quoting strings for shell use.
Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlStringShellQuoteConan(ConanFile):
    name = "perl-string-shellquote"
    version = "1.04-r5"
    description = "String::ShellQuote - quote strings for passing through the shell"
    license = "Perl"  # Same terms as Perl itself
    homepage = "https://metacpan.org/dist/String-ShellQuote"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR, then copy to standard package layout
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run(f'make install DESTDIR="{dest_dir}"', cwd=self.source_folder)

        # Find and copy .pm file to standard lib path
        pm_files = glob.glob(os.path.join(dest_dir, "**", "ShellQuote.pm"), recursive=True)
        if pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "String")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_files[0], target_dir)

        # Find and copy shell-quote CLI tool to bin/
        bin_files = glob.glob(os.path.join(dest_dir, "**", "shell-quote"), recursive=True)
        if bin_files:
            target_bin = os.path.join(self.package_folder, "bin")
            os.makedirs(target_bin, exist_ok=True)
            shutil.copy2(bin_files[0], target_bin)

    def package_info(self):
        # Pure Perl module: no C libraries to link
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
