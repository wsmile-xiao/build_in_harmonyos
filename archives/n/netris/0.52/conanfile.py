#!/usr/bin/env python3
"""Conan recipe for netris 0.52 — network Tetris game.

netris uses a custom Configure script (not autoconf/automake).
Build: ./Configure && make  (with Makefile patching for ncurses paths)
Install: manual copy of binary to prefix/bin
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class NetrisConan(ConanFile):
    name = "netris"
    version = "0.52"
    description = "Netris — a free networked version of Tetris"
    license = "GPL-2.0-or-later"
    homepage = "https://www.netris.org"
    url = "https://www.netris.org"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # Get ncurses paths from dependency
        ncurses_pkg = self.dependencies["ncurses"]
        ncurses_prefix = ncurses_pkg.package_folder
        ncurses_inc = os.path.join(ncurses_prefix, "include")
        ncurses_lib = os.path.join(ncurses_prefix, "lib")

        # Get compiler from Conan conf (R33: never use raw ${CC})
        compiler_executables = self.conf_info.get("tools.build:compiler_executables")
        cc = compiler_executables.get("c", "clang") if compiler_executables else "clang"

        # Step 1: Run Configure with safe values (no paths with '/')
        #   The Configure script uses sed s/-VAR-/$VAR/g which breaks with '/' in values
        #   So we don't pass any include/lib paths here
        self.run(
            f'bash Configure --cc "{cc}" --copt -O2 --cextra "-DNDEBUG"',
            cwd=self.source_folder,
        )

        # Step 2: Patch the generated Makefile to add ncurses include/lib paths
        #   Configure produces: LFLAGS = -lncurses (or similar, depending on detection)
        #   We need to replace LFLAGS with proper -L and -l flags
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(
            self,
            makefile,
            "CFLAGS = $(CEXTRA) $(COPT)",
            f"CFLAGS = $(CEXTRA) $(COPT) -I{ncurses_inc}",
        )
        # Patch LFLAGS to add library path (the -lncursesw part is already there from Configure)
        replace_in_file(
            self,
            makefile,
            "LFLAGS = ",
            f"LFLAGS = -L{ncurses_lib} -lncursesw",
        )

        # Step 3: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # netris has no install target; copy binary manually
        from conan.tools.files import copy
        copy(self, "netris", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sr", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
