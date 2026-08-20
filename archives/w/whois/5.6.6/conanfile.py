#!/usr/bin/env python3
"""Conan recipe — whois 5.6.6 (command-line WHOIS client).

whois uses a plain Makefile (no configure). The build requires:
1. perl to generate version.h from debian/changelog
2. make to compile whois binary

Platform adaptation: config.h needs HAVE_GETOPT_LONG defined for OHOS
(musl libc supports getopt_long but the upstream config.h doesn't detect it).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WhoisConan(ConanFile):
    name = "whois"
    version = "5.6.6"
    description = "WHOIS client for querying domain registration information"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rfc1036/whois"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Generate version.h from debian/changelog using perl
        perl = os.environ.get("PERL", "perl")
        self.run(f"{perl} make_version_h.pl debian/changelog > version.h", cwd=self.source_folder)

        # Build whois binary (R9: use -j1)
        self.run(f"make whois CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Install whois binary and man pages
        copy(self, "whois", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "whois.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "whois.conf.5", self.source_folder, os.path.join(self.package_folder, "share", "man", "man5"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
