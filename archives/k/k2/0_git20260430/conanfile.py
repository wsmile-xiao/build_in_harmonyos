#!/usr/bin/env python3
"""Conan recipe — k2 0_git20260430 (raw Makefile, C++ application).

k2 is a chess engine with UCI and Xboard interface (single executable,
GPL-3.0-or-later). Upstream: https://github.com/serg-meus/k2

Build notes:
- Upstream Makefile hardcodes CC=g++ (used as the C++ driver) and compiles
  with CFLAGS="-std=c++0x -Werror -Wall ... -Weffc++" (GCC-specific warning
  groups) + COPT="-O3 -DNDEBUG -DUSE_THREAD=true -flto" (kept as-is).
- The GCC-only warning groups are unknown to clang; combined with -Werror
  they abort the build, so the recipe passes the upstream warning set plus
  -Wno-unknown-warning-option on the make command line (override, no source
  patching).
- pthread symbols live in libc on OHOS, so -DUSE_THREAD=true needs no extra
  link flags.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class K2Conan(ConanFile):
    name = "k2"
    version = "0_git20260430"
    license = "GPL-3.0-or-later"
    author = "Sergey Meus"
    url = "https://github.com/serg-meus/k2"
    homepage = "https://github.com/serg-meus/k2"
    description = "K2 — chess engine with UCI and Xboard interface"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan profile conf, never from shell env
        # (empty on CI workers). tools.build:compiler_executables is a dict conf:
        # {"c": ..., "cpp": ...} — get it whole, then pick the C++ driver.
        comp_exe = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cxx = comp_exe.get("cpp")
        if not cxx:
            cxx = {"clang": "clang++", "gcc": "g++", "apple-clang": "clang++"}.get(
                str(self.settings.compiler), "c++")

        # Upstream CFLAGS (Makefile) + -Wno-unknown-warning-option for clang;
        # COPT ("-O3 -DNDEBUG -DUSE_THREAD=true -flto") stays from the Makefile.
        cflags = ("-std=c++0x -Werror -Wall -Wextra -Wpedantic "
                  "-Wcast-align -Wcast-qual -Wconversion -Wsign-conversion "
                  "-Wctor-dtor-privacy -Wnon-virtual-dtor -Wold-style-cast "
                  "-Woverloaded-virtual -Wredundant-decls -Wsign-promo "
                  "-Wshadow -Weffc++ -Wuninitialized "
                  "-Wno-unknown-warning-option")

        # R9: single job (HMDFS jobserver mkfifo is not permitted anyway)
        ret = self.run(f'make CC="{cxx}" CFLAGS="{cflags}" -j1',
                       cwd=self.source_folder, env="conanbuild")
        if ret != 0:
            raise ConanException(f"make failed with exit code {ret}")

    def package(self):
        # Single CLI executable; no headers/libraries to consume (R38: the
        # software-level commands.json declares it as a tool).
        copy(self, "k2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
