#!/usr/bin/env python3
"""Conan recipe — perl-ole-storage_lite (OLE::Storage_Lite) 0.24-r0.

Pure Perl module using ExtUtils::MakeMaker (perl Makefile.PL).
No C/XS compilation, no linking required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlolestorageliteConan(ConanFile):
    name = "perl-ole-storage_lite"
    version = "0.24-r0"
    description = "OLE::Storage_Lite - Simple Class for OLE document interface"
    license = "MIT"
    homepage = "https://metacpan.org/dist/OLE-Storage_Lite"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        # Use INSTALL_BASE=/ for predictable path: lib/perl5/OLE/Storage_Lite.pm
        self.run("perl Makefile.PL INSTALL_BASE=/")
        self.run("make")

    def package(self):
        # Install with DESTDIR to package folder
        self.run(f'make install DESTDIR="{self.package_folder}"')

    def package_info(self):
        # Perl module — expose lib path for consumers via runenv
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
