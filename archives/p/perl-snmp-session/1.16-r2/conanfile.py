#!/usr/bin/env python3
"""Conan recipe — SNMP::Session Perl module (ExtUtils::MakeMaker).

Pure Perl module for SNMP protocol access.
Build system: perl Makefile.PL + make + make install
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlSnmpSessionConan(ConanFile):
    name = "perl-snmp-session"
    version = "1.16-r2"
    description = "SNMP::Session - SNMP protocol access for Perl"
    license = "Artistic-2.0"
    homepage = "https://github.com/sleinen/snmp-session"
    url = ""  # CI fills this

    settings = "os", "arch", "build_type", "compiler"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported, require Linux or OHOS"
            )
        apply_conandata_patches(self)
        # Pure Perl module: use ExtUtils::MakeMaker
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install to package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}", env="conanbuild")
        # Copy .pm files to standard lib/perl5/ directory for G4 artifact check
        # Perl installs to deeply nested site_perl paths; flatten to lib/perl5/
        pm_files = glob.glob(
            os.path.join(self.package_folder, "**", "*.pm"),
            recursive=True,
        )
        for pm_file in pm_files:
            rel = os.path.relpath(pm_file, self.package_folder)
            # Find site_perl subdirectory; copy .pm files to lib/perl5/
            dst_dir = os.path.join(self.package_folder, "lib", "perl5")
            os.makedirs(dst_dir, exist_ok=True)
            copy(self, os.path.basename(pm_file), os.path.dirname(pm_file), dst_dir)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries (R26 not applicable)
        self.cpp_info.libs = []
        # Set up PERL5LIB so consumers can find the module
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
