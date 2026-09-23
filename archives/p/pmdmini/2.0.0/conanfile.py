#!/usr/bin/env python3
"""Conan recipe for pmdmini — C library for playing PMD/MDX chiptunes (NEC PC-98).

Build system: raw Makefile (no configure). Only the core static library
libpmdmini.a is packaged; the sample player pmdplay is NOT packaged because it
requires SDL2 (sdl2-config), which is an optional, non-library dependency.

Adaptation notes:
  - Upstream code is C++03-era. clang (default C++17) rejects the `-1`
    narrowing-to-uint8 in src/fmgen/psg.cpp:121 with -Wc++11-narrowing, so the
    C++ objects are compiled with -std=c++03 (matches Homebrew's
    `CXX="... -std=c++03"`).
  - fmgen / pmdwin / ppz8 are vendored (embedded) sources, not external deps.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PmdminiConan(ConanFile):
    name = "pmdmini"
    version = "2.0.0"
    description = "C library for playing PMD/MDX chiptunes (NEC PC-98)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mistydemeo/pmdmini"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core library has no external dependencies. The sample player
        # (pmdplay) needs sdl2, but is intentionally not packaged here.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compilers from Conan conf, never from shell env vars.
        # NOTE: conan 2.29.1 does not support "tools.build:compiler_executables:c"
        #       sub-key access; the conf is a single dict value, so fetch it whole.
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = executables.get("c", "clang")
        cxx = executables.get("cpp", "clang++")

        # Build only the core library via Makefile.lib (avoids the SDL2 player).
        # -std=c++03 is required: upstream is C++03-era code (see module docstring).
        # -fPIC: objects may later be linked into shared consumers.
        # Makefile.lib uses relative paths (src/fmgen, src/pmdwin, ...), so make
        # must run inside the source folder (basic_layout keeps build/ separate).
        self.run(
            f'make -f Makefile.lib CC="{cc}" CXX="{cxx} -std=c++03" '
            f'AR="llvm-ar" RANLIB="llvm-ranlib" CFLAGS="-fPIC -O2" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "pmdmini.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libpmdmini.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pmdmini"]
