#!/usr/bin/env python3
"""Conan recipe — Perl module (ExtUtils::MakeMaker / Makefile.PL).

perl-object-event 1.23-r0 — Object::Event: Perl event callback interface

Patch removes hard dependencies on common::sense and AnyEvent, replacing
them with standard Perl pragmas and a minimal inline guard implementation.
This makes the module self-contained for OHOS environments where these
CPAN modules are not pre-installed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlobjecteventConan(ConanFile):
    name = "perl-object-event"
    version = "1.23-r0"
    description = "Object::Event - Perl event callback interface"
    license = "perl"
    homepage = "https://metacpan.org/dist/Object-Event"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps (common::sense, AnyEvent) removed by patch — module is self-contained
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use INSTALL_BASE=/ so files install to lib/perl5/ under DESTDIR
        self.run("perl Makefile.PL INSTALL_BASE=/", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module - no C libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers (test_package) can find Object::Event
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
