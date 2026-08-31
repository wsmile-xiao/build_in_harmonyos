#!/usr/bin/env python3
"""Conan recipe for mp3cat 0.5 — CLI tool, plain hand-written Makefile build.

mp3cat copies a byte stream, skipping everything except MP3 frames with valid
headers.  It can read from stdin / an mp3dir and write to stdout / an mp3dir.

Upstream uses a plain Makefile (no configure script).  Patches:
  0001 — replace hardcoded `cc` with $(CC)/$(CFLAGS)/$(LDFLAGS) and add DESTDIR
  0002 — add --version / --help flags for CLI smoke-test compatibility
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Mp3catConan(ConanFile):
    name = "mp3cat"
    version = "0.5"
    description = "Copy a byte stream, skipping everything except MP3 frames with valid headers"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tomclegg/mp3cat"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use `in (..., ...)`, never `== "Linux"`
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mp3cat is adapted for Linux and OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler path from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Plain Makefile (no configure).  Build in source folder where the
        # Makefile lives (basic_layout puts build_folder in a separate subdir).
        # R26: static link for terminal tool.
        self.run(f'make CC="{cc}" CFLAGS="-O2" LDFLAGS="-static" -j1',
                 cwd=self.source_folder)

    def package(self):
        # Binary + scripts are built in the source folder (plain Makefile).
        copy(self, "mp3cat", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        for script in ("mp3log", "mp3log-conf", "mp3dirclean", "mp3http", "mp3stream-conf"):
            copy(self, script, src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Application — exports a binary on PATH, no libraries.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
