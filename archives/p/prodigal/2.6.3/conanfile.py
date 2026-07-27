#!/usr/bin/env python3
"""Conan recipe for Prodigal — microbial gene prediction tool.

Prodigal is a pure Makefile project (no configure script).
Build: make CC=clang LDFLAGS="-fuse-ld=ld.bfd"
Install: make install INSTALLDIR=<prefix>/bin
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ProdigalConan(ConanFile):
    name = "prodigal"
    version = "2.6.3"
    description = "Microbial gene prediction algorithm (PROkaryotic DynamIc Programming Genefinding ALgorithm)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/hyattpd/Prodigal"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf dict, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # Must use GNU ld (lld has compatibility issues on OHOS)
        ldflags = "-fuse-ld=/data/service/hnp/bin/ld.bfd"
        self.run(f'make -C {self.source_folder} CC="{cc}" LDFLAGS="{ldflags}" -j1')

    def package(self):
        copy(self, "prodigal", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # prodigal is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
