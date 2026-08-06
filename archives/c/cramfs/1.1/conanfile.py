#!/usr/bin/env python3
"""Conan recipe for cramfs 1.1 — compressed ROM file system tools.

Produces two executables: mkcramfs (create) and cramfsck (check).
Build system: GNU Makefile. Depends on zlib.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CramfsConan(ConanFile):
    name = "cramfs"
    version = "1.1"
    description = "Compressed ROM File System tools (mkcramfs/cramfsck)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/cramfs/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Get zlib include and lib paths from conan dependency
        zlib = self.dependencies["zlib"]
        cppflags = "-I."
        for inc_dir in zlib.cpp_info.includedirs:
            cppflags += f" -I{inc_dir}"

        ldflags = ""
        for lib_dir in zlib.cpp_info.libdirs:
            ldflags += f" -L{lib_dir}"

        # R9: Always use -j1; -C to run in source dir (basic_layout separates build dir)
        self.run(f"make -C {self.source_folder} CC={cc} CFLAGS='-fPIC -O2 -W -Wall' CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' LDLIBS='-lz' -j1")

    def package(self):
        copy(self, "mkcramfs", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cramfsck", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
