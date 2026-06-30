#!/usr/bin/env python3
"""Conan recipe — Net::CIDR (pure Perl module).

Net::CIDR manipulates IPv4/IPv6 netblocks in CIDR notation.
This is a pure Perl module built with ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetcidrConan(ConanFile):
    name = "perl-net-cidr"
    version = "0.27-r0"
    description = "Manipulate IPv4/IPv6 netblocks in CIDR notation (pure Perl module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://github.com/svarshavchik/Net-CIDR"
    url = ""  # CI fills this

    # Pure Perl module — no compiler/build_type needed
    settings = "os", "arch"

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
        cidr_files = glob.glob(os.path.join(dest_dir, "**", "Net", "CIDR.pm"), recursive=True)
        if cidr_files:
            # Copy to lib/perl5/Net/CIDR.pm for standard package layout
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "Net")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(cidr_files[0], target_dir)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
