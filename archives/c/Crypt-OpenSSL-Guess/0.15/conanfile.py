#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::Guess (pure Perl module).

Guess OpenSSL include and library paths.
Built with ExtUtils::MakeMaker (Makefile.PL).
Pure Perl — no XS, no compiled libraries.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CryptOpensslGuessConan(ConanFile):
    name = "crypt-openssl-guess"
    version = "0.15"
    description = "Guess OpenSSL include and library paths (pure Perl module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/Crypt::OpenSSL::Guess"

    # Pure Perl module — no compiler/build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — only Perl core modules
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run('make install DESTDIR="{}"'.format(dest_dir), cwd=self.source_folder)

        # Find the installed .pm file and copy to lib/perl5/ in package folder
        guess_files = glob.glob(
            os.path.join(dest_dir, "**", "Crypt", "OpenSSL", "Guess.pm"),
            recursive=True,
        )
        if not guess_files:
            raise Exception("Guess.pm not found in DESTDIR install output — package incomplete")
        target_dir = os.path.join(
            self.package_folder, "lib", "perl5", "Crypt", "OpenSSL"
        )
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(guess_files[0], target_dir)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
