#!/usr/bin/env python3
"""Conan recipe — dbview 1.0.4 (plain Makefile)

dbview prints the contents of dBase III/III+ database files.  It reads a .dbf
file and writes the records to stdout either as plain "field : value" lines, in
dBase browse form (-b), or as field descriptions (-e) and file information (-i).

Version 1.0.4 (2006-11-27) is a three-object plain-Makefile C program: there is
no configure script, no usable install target (the upstream one installs with
`-o root -g root` and uses the literal `MAN=man` value as the man page owner)
and no upstream test suite.  The recipe therefore builds with the compiler from
the Conan profile and installs the resulting binary and man page explicitly.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class DbviewConan(ConanFile):
    name = "dbview"
    version = "1.0.4"
    description = "Viewer for dBase III/III+ database files (records, field descriptions and file information)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.infodrom.org/projects/dbview/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: the tool is a plain POSIX C program, only Linux/OHOS are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler and flags come from the Conan profile/toolchain, never
        # from a bare ${CC}/${CFLAGS} in the shell environment.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        tc = GnuToolchain(self)
        # GnuToolchain.defines yields bare macro names (no "-D" prefix), the
        # Autotools helpers add the prefix themselves — do the same here.
        cflags = " ".join(tc.cflags + [f"-D{define}" for define in tc.defines])
        # R9: a three-object Makefile project — keep the build single job.
        # The upstream CFLAGS default (-O6 -fomit-frame-pointer -Wall -pipe) is
        # replaced by the profile flags; clang clamps the upstream -O6 to -O3.
        self.run(f'make -j1 CC="{cc}" CFLAGS="{cflags}"', cwd=self.source_folder)

    def package(self):
        copy(self, "dbview", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dbview.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
