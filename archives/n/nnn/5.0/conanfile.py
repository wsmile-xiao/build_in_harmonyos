#!/usr/bin/env python3
"""Conan recipe — nnn 5.0 (Makefile, CLI tool).

nnn (n³) is a small, lightning-fast file manager for the terminal.
Build system: plain Makefile (no configure script).
On HarmonyOS: requires readline (→ ncurses transitively), musl-fts.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NnnConan(ConanFile):
    name = "nnn"
    version = "5.0"
    description = "The unorthodox terminal file manager"
    license = "BSD-2-Clause"
    homepage = "https://github.com/jarun/nnn"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses (direct: nnn links libncursesw directly, not just via readline)
        self.requires("ncurses/6.6")
        # readline (depends on ncurses/6.6; provides libreadline + headers)
        self.requires("readline/8.3")
        # OHOS musl libc lacks fts_* functions; musl-fts provides libfts + fts.h
        self.requires("musl-fts/1.2.7")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Collect dependency include/lib paths
        inc_flags = []
        lib_flags = []

        # readline (direct dependency; also provides ncurses headers transitively)
        readline = self.dependencies.get("readline")
        if readline:
            for d in readline.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(readline.package_folder, d)}")
            for d in readline.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(readline.package_folder, d)}")

        # ncurses (transitive from readline, but nnn needs ncursesw directly)
        ncurses = self.dependencies.get("ncurses")
        if ncurses:
            for d in ncurses.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(ncurses.package_folder, d)}")
            for d in ncurses.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(ncurses.package_folder, d)}")

        # musl-fts (fts.h + libfts for OHOS)
        fts = self.dependencies.get("musl-fts")
        if fts:
            for d in fts.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(fts.package_folder, d)}")
            for d in fts.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(fts.package_folder, d)}")

        # Build type → optimization flags
        opt = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

        # nnn Makefile uses CFLAGS += for -std=c11 -Wall -Wextra -Wshadow
        # Command-line CFLAGS overrides Makefile's, so include all needed flags.
        # LDLIBS overridden entirely: -lreadline -lncursesw -lfts -lpthread
        # (Makefile's += won't append to command-line value)
        cflags = f"-std=c11 -Wall -Wextra -Wshadow {opt} {' '.join(inc_flags)}"
        ldflags = " ".join(lib_flags)
        ldlibs = "-lreadline -lncursesw -lfts -lpthread"

        # R9: Always use -j1
        self.run(
            f'make CC={cc} CFLAGS="{cflags}" LDFLAGS="{ldflags}" LDLIBS="{ldlibs}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # nnn is a single binary; copy to bin/
        copy(self, "nnn", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Man page
        copy(self, "nnn.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))
        # License
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # If musl-fts is shared, pass its runtime lib path for consumers
        fts = self.dependencies.get("musl-fts")
        if fts and fts.options.shared:
            fts_libdir = os.path.join(fts.package_folder, fts.cpp_info.libdirs[0])
            self.runenv_info.append_path("LD_LIBRARY_PATH", fts_libdir)
