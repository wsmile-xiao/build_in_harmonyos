#!/usr/bin/env python3
"""Conan recipe for perl-ntlm 1.09.6 (Authen::NTLM).

Pure Perl module using ExtUtils::MakeMaker (perl Makefile.PL + make).
Build: perl Makefile.PL && make && make install DESTDIR=...
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlntlmConan(ConanFile):
    name = "perl-ntlm"
    version = "1.09.6"
    description = "Perl module for NTLM authentication (Authen::NTLM)"
    license = "Artistic-1.0 OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/NTLM"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Generate Makefile using ExtUtils::MakeMaker
        # Use a simple INSTALL_BASE for staging
        self.run("perl Makefile.PL")
        self.run("make -j2")

    def package(self):
        # Install directly to package folder using DESTDIR
        # make install with INSTALLSITELIB / INSTALLBASE
        # Use blib directory which contains the built modules
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"), dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # Pure Perl module - no shared libraries
        self.cpp_info.libs = []
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl lib path: {perl_lib}")
