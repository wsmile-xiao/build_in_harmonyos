#!/usr/bin/env python3
"""Conan recipe — perl-net-rblclient 0.5-r8 (Pure Perl module).

Build system: perl Makefile.PL + make + make install
This is a pure Perl module (no XS/C code), so static linking (R26) is N/A.
Dependencies (IO::Socket, Time::HiRes, Net::DNS::Packet) are Perl core/standard
modules, not Conan packages, so requirements() is empty.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetrblclientConan(ConanFile):
    name = "perl-net-rblclient"
    version = "0.5-r8"
    description = "Queries multiple Realtime Blackhole Lists in parallel"
    license = "Perl Artistic"
    homepage = "https://metacpan.org/pod/Net::RBLClient"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl core modules (IO::Socket, Time::HiRes, Net::DNS::Packet)
        # are not Conan packages — no external Conan dependencies.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Use INSTALL_BASE=/ so install paths are relative (lib/, bin/)
        # DESTDIR in package() will prepend the Conan package folder
        self.run('perl Makefile.PL INSTALL_BASE=/')
        self.run("make")

    def package(self):
        # DESTDIR prepends package_folder to the relative install paths
        self.run(f'make install DESTDIR="{self.package_folder}"')

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Set PERL5LIB so consumers can find the Perl module
        for lib_dir in glob.glob(os.path.join(self.package_folder, "lib", "*")):
            if os.path.isdir(lib_dir):
                self.runenv_info.append_path("PERL5LIB", lib_dir)
