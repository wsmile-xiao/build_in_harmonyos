#!/usr/bin/env python3
"""Conan recipe — perl-net-ipv4addr 0.10-r7 (pure Perl module).

Net::IPv4Addr provides functions for manipulating IPv4 addresses.
Build system: ExtUtils::MakeMaker (perl Makefile.PL → make → make install)
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Perlnetipv4AddrConan(ConanFile):
    name = "perl-net-ipv4addr"
    version = "0.10-r7"
    description = "Perl extension for manipulating IPv4 addresses"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/Net-IPv4Addr"
    url = ""  # CI fills this

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
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find the installed .pm file and copy to lib/ in package folder
        pm_files = glob.glob(
            os.path.join(dest_dir, "**", "Net", "IPv4Addr.pm"),
            recursive=True,
        )
        if pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "Net")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_files[0], target_dir)

        # Also copy the ipv4calc script if present
        script_files = glob.glob(
            os.path.join(dest_dir, "**", "bin", "ipv4calc"),
            recursive=True,
        )
        if script_files:
            target_bin = os.path.join(self.package_folder, "bin")
            os.makedirs(target_bin, exist_ok=True)
            shutil.copy2(script_files[0], target_bin)

    def package_info(self):
        self.cpp_info.libs = []
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
