#!/usr/bin/env python3
"""Conan recipe for perl-net-telnet 3.05-r1 (pure Perl module).

Net::Telnet - Interact with TELNET port or other TCP ports.
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlNetTelnetConan(ConanFile):
    name = "perl-net-telnet"
    version = "3.05-r1"
    description = "Interact with TELNET port or other TCP ports"
    license = "Artistic-1.0-Perl"  # Same terms as Perl itself
    homepage = "https://metacpan.org/dist/Net-Telnet"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install using Makefile install to a temporary staging area
        # Then copy .pm files to lib/ for standard Conan layout
        self.run(f'make install DESTDIR="{self.package_folder}"', env="conanbuild")

        # Find and copy .pm files to standard lib/ directory for G4 compatibility
        for pm_file in glob.glob(os.path.join(self.package_folder, "**", "*.pm"), recursive=True):
            # Get the relative path from the staging root
            rel = os.path.relpath(pm_file, self.package_folder)
            # Try to find the "Net" directory in the path and preserve it
            parts = rel.split(os.sep)
            if "Net" in parts:
                net_idx = parts.index("Net")
                new_rel = os.path.join("lib", *parts[net_idx:])
            else:
                new_rel = os.path.join("lib", os.path.basename(pm_file))
            dest = os.path.join(self.package_folder, new_rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            copy(self, os.path.basename(pm_file), os.path.dirname(pm_file),
                 os.path.dirname(dest))

    def package_info(self):
        # Pure Perl module - expose the lib directory for Perl imports
        self.cpp_info.libs = []  # No compiled libs
        self.cpp_info.libdirs = ["lib"]
