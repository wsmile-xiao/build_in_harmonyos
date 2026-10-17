#!/usr/bin/env python3
"""Conan recipe — Set::IntSpan Perl module (ExtUtils::MakeMaker).

Pure Perl module for managing sets of integers, newsrc style.
Build system: perl Makefile.PL + make + make install
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlSetIntSpanConan(ConanFile):
    name = "perl-set-intspan"
    version = "1.19-r5"
    description = "Set::IntSpan - manages sets of integers, newsrc style"
    license = "unknown"  # CPAN license field is "unknown"
    homepage = "https://metacpan.org/release/Set-IntSpan"
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
        # Copy .pm files to standard lib/ directory for G4 artifact check
        # Perl installs to deeply nested paths; flatten to lib/perl5/
        src_dirs = glob.glob(
            os.path.join(self.package_folder, "**", "Set"),
            recursive=True,
        )
        for src_dir in src_dirs:
            if os.path.isdir(src_dir):
                # Copy to lib/perl5/Set/
                dst = os.path.join(self.package_folder, "lib", "perl5", "Set")
                os.makedirs(dst, exist_ok=True)
                copy(self, "*.pm", src_dir, dst)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries (R26 not applicable)
        self.cpp_info.libs = []
        # Set up PERL5LIB so consumers can find the module
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
