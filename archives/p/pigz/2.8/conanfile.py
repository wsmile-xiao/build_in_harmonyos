#!/usr/bin/env python3
"""Conan recipe for pigz 2.8 — parallel gzip compressor using pthreads.

pigz is a command-line tool that compresses files in parallel using
multiple threads. It is a raw Makefile project (no configure script).

Dependencies:
  - zlib/1.3.1 (published on ohpcd)

OHOS adaptation (patches in conandata.yml):
  - Makefile: change `ln -f pigz unpigz` to `ln -sf pigz unpigz`
    (HMDFS does not support hard links).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PigzConan(ConanFile):
    name = "pigz"
    version = "2.8"
    description = "Parallel gzip compressor using pthreads"
    license = "Zlib"
    homepage = "https://zlib.net/pigz/"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pigz is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Get zlib include/lib paths from dependency
        zlib = self.dependencies["zlib"]
        zlib_inc = zlib.cpp_info.includedirs
        zlib_lib = zlib.cpp_info.libdirs

        cflags = "-O3 -Wall -Wextra -Wno-unknown-pragmas -Wcast-qual -fPIC"
        for inc in zlib_inc:
            cflags += f" -I{inc}"

        ldflags = ""
        for lib in zlib_lib:
            ldflags += f" -L{lib}"

        # R9: Always use -j1
        self.run(
            f'make CC={cc} CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
            f'LIBS="-lm -lpthread -lz" -j1 pigz',
            cwd=self.source_folder
        )

    def package(self):
        copy(self, "pigz", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "unpigz", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "pigz.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
