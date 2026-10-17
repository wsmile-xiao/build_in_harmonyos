#!/usr/bin/env python3
"""Conan recipe — ttyplot 1.7.1 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TtyplotConan(ConanFile):
    name = "ttyplot"
    version = "1.7.1"
    description = "Realtime plotting utility for terminal with data input from stdin"
    license = "Apache-2.0"
    homepage = "https://github.com/tenox7/ttyplot"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan profile conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # ncurses/6.5 (Conan dependency) provides headers and libncursesw.a.
        # The Makefile uses `pkg-config --cflags/libs ncursesw` via backtick
        # substitution, but we bypass pkg-config by passing CFLAGS and LDLIBS
        # on the make command line — GNU make gives command-line variables
        # priority over Makefile += assignments.
        ncurses = self.dependencies["ncurses"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")

        cflags = f"-Wall -Wextra -I{ncurses_inc}"
        ldlibs = f"-L{ncurses_lib} -lncursesw -lm"

        # R9: Always use -j1
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDLIBS="{ldlibs}" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "ttyplot", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "ttyplot.1", self.source_folder, os.path.join(self.package_folder, "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
