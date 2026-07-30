#!/usr/bin/env python3
"""Conan recipe — dos2unix 7.5.4

dos2unix/unix2dos: DOS/MAC to Unix text format converter with Unicode UTF-16 support.
Pure Makefile project, no configure script. NLS disabled (HarmonyOS lacks libintl/gettext).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Dos2UnixConan(ConanFile):
    name = "dos2unix"
    version = "7.5.4"
    description = "DOS/MAC to Unix text format converter with Unicode UTF-16 support"
    license = "BSD-2-Clause"
    homepage = "https://waterlan.home.xs4all.nl/dos2unix.html"
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

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"

        # R9: Use -j1
        # Patch 0001 disables ENABLE_NLS (set to empty) and changes LINK to cp -f
        self.run(f"make CC={cc} -j1 dos2unix unix2dos mac2unix unix2mac", cwd=self.source_folder)

    def package(self):
        # Copy executables to bin/
        copy(self, "dos2unix", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "unix2dos", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mac2unix", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "unix2mac", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man pages to man/man1/
        copy(self, "dos2unix.1", self.source_folder, os.path.join(self.package_folder, "man", "man1"))
        copy(self, "unix2dos.1", self.source_folder, os.path.join(self.package_folder, "man", "man1"))
        copy(self, "mac2unix.1", self.source_folder, os.path.join(self.package_folder, "man", "man1"))
        copy(self, "unix2mac.1", self.source_folder, os.path.join(self.package_folder, "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

