#!/usr/bin/env python3
"""Conan recipe for sl (Steam Locomotive) — a classic terminal animation command.

sl displays an animated steam locomotive when you accidentally type 'sl'
instead of 'ls'. This recipe builds the binary from source using a simple
Makefile, linking against ncurses (wide-char version).

Key adaptation points:
  - Makefile uses `?=` for CC/CFLAGS/CPPFLAGS/LDFLAGS so Conan env overrides
  - ncursesw (wide-char) is used instead of ncurses for Unicode support
  - -ltinfo removed (bundled into libncursesw in the OHOS ncurses package)
  - CC comes from Conan conf (R33: never use shell env vars in build())
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class SlConan(ConanFile):
    name = "sl"
    version = "5.02-r1"
    description = "sl (Steam Locomotive) — a classic terminal animation command"
    license = "MIT"
    homepage = "https://github.com/mtoyoda/sl"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Get ncurses include and lib paths from the dependency
        ncurses = self.dependencies["ncurses"]
        inc_dirs = ncurses.cpp_info.includedirs
        lib_dirs = ncurses.cpp_info.libdirs
        # Resolve to absolute paths using the package folder
        inc_flags = " ".join(f"-I{os.path.join(ncurses.package_folder, d)}" for d in inc_dirs)
        lib_flags = " ".join(f"-L{os.path.join(ncurses.package_folder, d)}" for d in lib_dirs)

        # R9: Always use -j1
        self.run(f'make CC={cc} CPPFLAGS="{inc_flags}" LDFLAGS="{lib_flags}" -j1',
                 cwd=self.source_folder)

    def package(self):
        copy(self, "sl", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["ncurses::ncurses"]
