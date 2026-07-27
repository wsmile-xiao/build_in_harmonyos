#!/usr/bin/env python3
"""Conan recipe for figlet 2.2.5 — CLI ASCII art text generator.

figlet is a program for making large letters out of ordinary text.
It uses a plain Makefile (no configure script).

Build: make CC=clang LD=clang CFLAGS=... XCFLAGS=-DTLF_FONTS prefix=... all
Install: copy binaries, man pages, fonts to package folder
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FigletConan(ConanFile):
    name = "figlet"
    version = "2.2.5"
    description = "FIGlet is a program for making large letters out of ordinary text"
    license = "MIT"
    homepage = "https://www.figlet.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # figlet uses a plain Makefile. Run from source folder since
        # basic_layout creates a build-release subdirectory.
        fontdir = os.path.join(self.package_folder, "share", "figlet")
        os.chdir(self.source_folder)

        # R33: Get compiler from Conan conf, not hardcoded
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # Pass DEFAULTFONTDIR/DEFAULTFONTFILE as make variables (not -D in XCFLAGS)
        # because the Makefile's .c.o rule already appends -DDEFAULTFONTDIR and
        # -DDEFAULTFONTFILE after XCFLAGS, which would cause macro redefinition
        # warnings and silently override our paths with the Makefile defaults.
        self.run(
            f'make CC="{cc}" LD="{cc}" '
            f'CFLAGS="-fPIC -O2 -Wall" '
            f'XCFLAGS="-DTLF_FONTS" '
            f'DEFAULTFONTDIR="{fontdir}" '
            f'DEFAULTFONTFILE="standard" '
            f"-j1 all"
        )

    def package(self):
        src = self.source_folder
        # Copy built binaries and shell scripts
        copy(self, "figlet", src, os.path.join(self.package_folder, "bin"))
        copy(self, "chkfont", src, os.path.join(self.package_folder, "bin"))
        copy(self, "figlist", src, os.path.join(self.package_folder, "bin"))
        copy(self, "showfigfonts", src, os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.6", src, os.path.join(self.package_folder, "man", "man6"))
        # Copy font files
        copy(self, "*.flf", os.path.join(src, "fonts"), os.path.join(self.package_folder, "share", "figlet"))
        copy(self, "*.flc", os.path.join(src, "fonts"), os.path.join(self.package_folder, "share", "figlet"))

    def package_info(self):
        # figlet is a CLI tool — expose bindirs for consumers
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "man"]
