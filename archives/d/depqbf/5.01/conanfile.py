#!/usr/bin/env python3
"""Conan recipe for DepQBF 5.01.

DepQBF is a search-based solver for quantified boolean formulae (QBF) in
prenex conjunctive normal form (QDIMACS). Upstream 5.01 is a pure Makefile
project (no configure, no cmake): `make` builds the `depqbf` CLI binary and
the static library `libqdpll.a` (C API declared in `qdpll.h`).

Build targets are invoked explicitly (`libqdpll.a depqbf`) so the Linux-only
shared-library branch (`libqdpll.so`, -soname) is never built on OHOS.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DepqbfConan(ConanFile):
    name = "depqbf"
    version = "5.01"
    description = "DepQBF, a solver for quantified boolean formulae (QBF)"
    license = "GPL-3.0-or-later"
    homepage = "https://lonsing.github.io/depqbf/"
    url = ""
    topics = "qbf", "solver", "qdpll", "sat"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "depqbf 5.01 only builds the static library libqdpll.a "
                "(upstream makefile has no portable shared target on OHOS)"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf, never from shell env vars.
        # The ohos-aarch64 profile registers tools.build:compiler_executables
        # as a dict ({c, cpp, ar, ranlib}); the `:c` sub-key form is NOT a
        # registered conf, so read the dict and index it.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # R9: always -j1. Build only the static lib and the CLI binary;
        # this skips the Linux -soname shared branch entirely.
        # NOTE: upstream libqdpll.a rule hardcodes `ar`/`ranlib` (ignores
        # AR/RANLIB vars); plain `ar` on the worker creates the archive fine.
        self.run(f"make CC={cc} -j1 libqdpll.a depqbf", cwd=self.source_folder)

    def package(self):
        copy(self, "qdpll.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libqdpll.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "depqbf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["qdpll"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "depqbf")
        self.cpp_info.set_property("cmake_target_name", "depqbf::qdpll")
