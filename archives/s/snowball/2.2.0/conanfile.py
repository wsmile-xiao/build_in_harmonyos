#!/usr/bin/env python3
"""Conan recipe — snowball 2.2.0 (Snowball stemming algorithms for C)

Upstream: https://snowballstem.org/ (BSD-3-Clause)
Build system: single GNUmakefile, no configure script.

The makefile bootstraps the snowball compiler (host tool built with the
same CC) and uses it to generate the C sources of all 29 stemming
algorithms, archived together with the runtime into libstemmer.a.
algorithms.mk / libstemmer_c.in / modules.h are generated on the fly by
the perl scripts in libstemmer/ (env-shebang), so perl must be on PATH
(provided by the ohos-aarch64 profile buildenv).

Test integration (L1): build() runs the self-contained upstream target
`check_stemtest` (tests/stemtest.c, 8 regression cases). The remaining
48 data-driven `make check` targets require the external snowball-data
repository (~500 MB, never bundled) — executed in full on the adaptation
machine against the release-date snapshot of the data repo; see
notes.md for the run log and statistics.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class SnowballConan(ConanFile):
    name = "snowball"
    version = "2.2.0"
    description = "Snowball stemming algorithms — libstemmer C library (29 languages) plus the stemwords CLI"
    license = "BSD-3-Clause"
    homepage = "https://snowballstem.org/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: compiler & tools come from Conan conf, never bare shell env.
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict)
        cc = ce.get("c") or "clang"
        ar = ce.get("ar") or "llvm-ar"
        ranlib = ce.get("ranlib") or "llvm-ranlib"

        # R9: -j1 (HMDFS jobserver fifo safety on parallel makes).
        # Targets: static lib + CLI. `all` would also build the snowball
        # compiler only — same toolchain, no extra deps.
        self.run(
            f'make -j1 CC="{cc}" AR="{ar}" RANLIB="{ranlib}" libstemmer.a stemwords'
        )

        # Upstream self-contained regression suite (part of `make check`
        # that needs no external data repo): 8 embedded cases — emoji
        # mutation, U+40079 private-use codepoint and numeric-damage
        # regressions (#66/#81) iterating over all 29 algorithms.
        self.run(
            f'make -j1 CC="{cc}" AR="{ar}" RANLIB="{ranlib}" check_stemtest'
        )

    def package(self):
        # Public API surface is exactly one self-contained header
        # (zero #include, C++ guarded) + the static archive + the CLI.
        copy(self, "libstemmer.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libstemmer.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "stemwords",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["stemmer"]
        self.cpp_info.set_property("cmake_file_name", "snowball")
        self.cpp_info.set_property("cmake_target_name", "snowball::snowball")
