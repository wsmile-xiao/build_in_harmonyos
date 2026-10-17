#!/usr/bin/env python3
"""Conan recipe for uc-echo 1.12 — bare Makefile application (six CLI tools).

Upstream: http://uc-echo.sourceforge.net/ (BSD-2-Clause, 2011, x86-era C++03/TR1).
HarmonyOS PC (OHOS aarch64) adaptation points, see notes.md for evidence:
  - TR1 -> C++11 std modernization (OHOS libc++ ships no <tr1/*> headers)
  - MMAP.hpp: explicit <unistd.h> (close() not transitively declared)
  - -fsigned-char: index_t=char stores -1; aarch64 plain char is unsigned
  - K0: --version/--help added to the shared Options parser (util.hpp)
"""
import os

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UcechoConan(ConanFile):
    name = "uc-echo"
    version = "1.12"
    description = "ECHO: reference-free short-read error correction for NGS data (six CLI tools)"
    license = "BSD-2-Clause"
    homepage = "http://uc-echo.sourceforge.net/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # URL ends with "/download" (no extension) -> pass filename so conan
        # can detect the tar.gz format from the local name.
        get(self, filename="echo_v1_12.tgz", **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never from bare shell env.
        # tools.build:compiler_executables is a dict {"c": ..., "cpp": ...}.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp.get("cpp", "clang++")
        # R9: -j1. -fsigned-char keeps upstream x86 char semantics on aarch64.
        # Bare Makefile lives in the source folder; conan build() runs in the build folder.
        self.run('make -C "%s" CXX="%s" CXXFLAGS="-Wall -O3 -m64 -fsigned-char" -j1'
                 % (self.source_folder, cxx))

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("hashing", "HashMerge", "NeighborJoin", "NeighborJoinParam", "NeighborMerge", "Voting"):
            copy(self, tool, src, bindir)
        copy(self, "LICENSE", src, self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
