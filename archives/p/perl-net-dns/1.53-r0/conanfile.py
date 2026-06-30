#!/usr/bin/env python3
"""Conan recipe — Net::DNS Perl module.

Net::DNS is a Perl Interface to the Domain Name System.
Build system: perl Makefile.PL + make (ExtUtils::MakeMaker)
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetdnsConan(ConanFile):
    name = "perl-net-dns"
    version = "1.53-r0"
    description = "Perl Interface to the Domain Name System"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-DNS"
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
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find the installed Net/ directory and copy to lib/perl5/ in package folder
        net_dirs = glob.glob(os.path.join(dest_dir, "**", "Net"), recursive=True)
        if net_dirs:
            target_dir = os.path.join(self.package_folder, "lib", "perl5")
            # Copy the entire Net/ tree (includes DNS.pm, DNS/, DNS/RR/, etc.)
            for net_dir in net_dirs:
                # Walk up to find the lib/ parent
                parent = os.path.dirname(net_dir)
                if os.path.basename(parent) == "lib":
                    # Copy everything under lib/ to package lib/perl5/
                    for item in os.listdir(parent):
                        src = os.path.join(parent, item)
                        dst = os.path.join(target_dir, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                    break

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
