#!/usr/bin/env python3
"""Conan recipe for htpdate 1.3.7 — Makefile project.

htpdate is a tool for synchronizing system time via HTTP time protocol.
It fetches timestamps from remote web servers and adjusts local system time.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy

class HtpdateConan(ConanFile):
    name = "htpdate"
    version = "1.3.7"
    description = "Synchronize system time via HTTP time protocol"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/twekkel/htpdate"
    url = "https://github.com/twekkel/htpdate"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Patch uses #ifdef __linux__ (compiler-predefined macro) for adjtimex compat
        # Makefile uses CC ?= gcc, CFLAGS += ...; pass CC and CFLAGS explicitly
        cc = os.environ.get("CC", "clang")
        if self.settings.build_type == "Debug":
            opt = "-g -O0"
        else:
            opt = "-O2"
        cflags = f"-Wall -std=c11 -pedantic {opt}"
        self.run(f'make CC={cc} CFLAGS="{cflags}" -j1')

    def package(self):
        # Makefile install target requires install/strip/gzip which may be missing
        # on OHOS; manually copy the binary and man page
        copy(self, "htpdate", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "htpdate.8", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
