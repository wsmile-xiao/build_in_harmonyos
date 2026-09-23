#!/usr/bin/env python3
"""Conan recipe — exifprobe 2.0.1 (EXIF/image metadata probe CLI).

Upstream: plain Makefile (no configure). Produces the `exifprobe` CLI
binary plus the `exifgrep` shell wrapper and man pages.
Adapted for HarmonyOS OHOS (aarch64): compiler taken from Conan conf
(R33), make -j1 (R9), no shared-library system-name conflicts.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class ExifprobeConan(ConanFile):
    name = "exifprobe"
    version = "2.0.1"
    description = "EXIF probe — reads and reports metadata from digital image files (JPEG/TIFF/CIFF/JP2/MRW/RAF/X3F)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hfiguiere/exifprobe"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("exifprobe requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        # R33: compiler from Conan conf, never ${CC}; R9: -j1
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"make -j1 CC={cc} \"CFLAGS=-DCOLOR -O2\"")

    def package(self):
        copy(self, "exifprobe", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "exifgrep", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "exifprobe.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))
        copy(self, "exifgrep.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
