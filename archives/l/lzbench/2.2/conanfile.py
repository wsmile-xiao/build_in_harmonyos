#!/usr/bin/env python3
"""Conan recipe for lzbench 2.2 — In-memory benchmark of open-source compressors.

lzbench is a compression benchmark tool that bundles many compression
libraries (zstd, brotli, lz4, xz, etc.) as source code. It uses a plain
Makefile (no configure, no make install). The build produces a single
`lzbench` binary.

Packaged as an application (command-line tool), not a library.

No third-party conan dependencies — all compression libraries are bundled.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LzbenchConan(ConanFile):
    name = "lzbench"
    version = "2.2"
    description = "In-memory benchmark of open-source compressors"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/inikep/lzbench"
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
        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        # R9: Always use -j1; run in source folder where Makefile lives
        self.run(f"make CC={cc} CXX={cxx} -j1", cwd=self.source_folder)

    def package(self):
        # No make install target — manually copy the binary
        copy(self, "lzbench", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
