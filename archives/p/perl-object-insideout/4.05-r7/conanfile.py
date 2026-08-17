#!/usr/bin/env python3
"""Conan recipe — perl-object-insideout 4.05-r7 (Pure Perl module).

Build system: ExtUtils::MakeMaker (perl Makefile.PL + make + make install)
This is a pure Perl module with no C/XS compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlobjectinsideoutConan(ConanFile):
    name = "perl-object-insideout"
    version = "4.05-r7"
    description = "Comprehensive inside-out object support module for Perl"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/release/Object-InsideOut"
    url = ""  # CI fills this

    # R32: settings.os must include both Linux and OHOS
    # L0p: settings must include all four for OHOS profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Object::InsideOut has a hard runtime dependency on Exception::Class 1.32.
        # perl-exception-class is not yet published to the Conan registry.
        # When it becomes available, add: self.requires("perl-exception-class/<version>")
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        # Set env to avoid interactive prompts
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use a temporary prefix for clean installation (no DESTDIR nesting)
        self._prefix = os.path.join(self.build_folder, "perl_prefix")
        self.run(f'perl Makefile.PL INSTALL_BASE="{self._prefix}"', cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Install directly to the temporary prefix (no DESTDIR)
        self.run("make install", cwd=self.source_folder)
        # Copy Perl module files from prefix/lib/perl5/ to package/lib/perl5/
        perl_lib = os.path.join(self._prefix, "lib", "perl5")
        copy(self, "*.pm", perl_lib, os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pod", perl_lib, os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # Pure Perl module — no C/C++ libraries
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
