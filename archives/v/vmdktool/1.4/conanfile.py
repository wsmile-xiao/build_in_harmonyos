#!/usr/bin/env python3
"""Conan recipe for vmdktool 1.4 — BSD-style Makefile (no configure script).

vmdktool converts raw filesystems to VMDK files and vice versa.
Build system: simple BSD Makefile (CC, CFLAGS, LDLIBS, PREFIX, DESTDIR).
License: BSD-2-Clause.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class VmdktoolConan(ConanFile):
    name = "vmdktool"
    version = "1.4"
    description = "Converts raw filesystems to VMDK files and vice versa"
    license = "BSD-2-Clause"
    homepage = "https://people.freebsd.org/~brian/vmdktool/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Get zlib static library from Conan dependency (R26: static link)
        zlib = self.dependencies["zlib"]
        zlib_lib_dir = os.path.join(zlib.package_folder, "lib")
        if not os.path.isdir(zlib_lib_dir):
            zlib_lib_dir = zlib.package_folder
        zlib_static = os.path.join(zlib_lib_dir, "libz.a")
        if not os.path.isfile(zlib_static):
            zlib_static = f"-L{zlib_lib_dir} -lz"

        cflags = "-fPIC -O2 -pipe"
        ldlibs = zlib_static

        self.run(
            f'make -j1 CC="{cc}" CFLAGS="{cflags}" LDLIBS="{ldlibs}"',
            cwd=self.source_folder
        )

    def package(self):
        # vmdktool is a command-line tool: install the binary to bin/
        copy(self, "vmdktool", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install man page if present
        copy(self, "vmdktool.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
