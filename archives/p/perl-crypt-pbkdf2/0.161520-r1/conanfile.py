#!/usr/bin/env python3
"""Conan recipe — Crypt::PBKDF2 (pure Perl module).

Crypt::PBKDF2 implements the PBKDF2 password hash algorithm.
This is a pure Perl module built with ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptPbkdf2Conan(ConanFile):
    name = "perl-crypt-pbkdf2"
    version = "0.161520-r1"
    description = "The PBKDF2 password hash algorithm (pure Perl module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-PBKDF2"
    url = ""  # CI fills this

    # CI L0p requires all four settings even for pure Perl modules
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Pure Perl module — Perl runtime dependencies are managed by CPAN
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

        # Find the installed Crypt directory containing PBKDF2.pm
        pbkdf2_files = glob.glob(
            os.path.join(dest_dir, "**", "Crypt", "PBKDF2.pm"),
            recursive=True,
        )
        if not pbkdf2_files:
            raise Exception("Crypt/PBKDF2.pm not found in install output")

        # The Crypt directory is the parent of PBKDF2.pm
        crypt_dir = os.path.dirname(pbkdf2_files[0])
        # Copy the entire Crypt directory tree to lib/perl5/Crypt/
        target_crypt_dir = os.path.join(self.package_folder, "lib", "perl5", "Crypt")
        shutil.copytree(crypt_dir, target_crypt_dir, dirs_exist_ok=True)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
