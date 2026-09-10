#!/usr/bin/env python3
"""Conan recipe — cohomcalg 0.32

Line-bundle sheaf cohomology computation tool for toric varieties
(arXiv:1003.5217). Pure Makefile project (no configure/CMake), embeds a
modified PolyLib in source/polylib_mod; links only -lpthread (C++11 std::thread).

Build system notes:
  - Top-level Makefile hardcodes `CC := g++` / `LD := g++`; the OHOS CI
    image provides clang/clang++ (no g++), so we override CC/LD on the
    command line.
  - patch 0001 fixes a C++11 user-defined-literal error in matrix.c
    (`" "P_VALUE_FMT" "` -> `" " P_VALUE_FMT " "`) under clang++ strict
    parsing (P_VALUE_FMT expands via string concat).
  - Makefile has no `install` target; package() copies the built binary.

License: GPL-3.0 (upstream + embedded PolyLib are GPL-3.0)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CohomcalgConan(ConanFile):
    name = "cohomcalg"
    version = "0.32"
    description = "cohomCalg — computation of sheaf cohomologies for line bundles on toric varieties (arXiv:1003.5217)"
    license = "GPL-3.0"
    homepage = "https://github.com/BenjaminJurke/cohomCalg"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: embeds modified PolyLib, C++11 std::thread only
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform support
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: never bare ${CC}/${CXX} shell vars — resolve from Conan conf
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("cpp") or comp_execs.get("c") or "clang++"
        # Makefile hardcodes g++; OHOS CI has clang++ only. Override CC/LD.
        # Makefile defines DEFS := -DPOLYLIB_BITS=64 itself.
        # R9: -j1 for old single make project (also avoids jobserver fifo issue)
        self.run(f'make -j1 CC="{cc}" LD="{cc}"', cwd=self.source_folder)

    def package(self):
        # CLI tool: install the built binary to bin/ (Makefile has no install target)
        copy(self, "cohomcalg", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")