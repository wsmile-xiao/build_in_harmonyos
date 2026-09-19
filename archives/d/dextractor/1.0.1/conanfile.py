#!/usr/bin/env python3
"""Conan recipe — dextractor 1 (Makefile CLI tools)

Upstream: https://github.com/thegenemyers/DEXTRACTOR
8 CLI tools: dextract dexta undexta dexar undexar dexqv undexqv dex2DB
dextract/dex2DB additionally need HDF5 + zlib.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DextractorConan(ConanFile):
    name = "dextractor"
    version = "1.0.1"
    description = "Dextractor and compression command library for PacBio sequence data"
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/DEXTRACTOR"
    url = "https://github.com/thegenemyers/DEXTRACTOR"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _tools = ("dextract", "dexta", "undexta", "dexar", "undexar", "dexqv", "undexqv", "dex2DB")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # dextract / dex2DB link against HDF5 + zlib (libaec comes via hdf5)
        self.requires("hdf5/1.14.6")
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Makefile patched to use $(CC) (see patches/0010), so pass the OHOS
        # clang executable from the Conan profile directly (R33: no bare shell env vars).
        hdf5 = self.dependencies["hdf5"]
        zlib = self.dependencies["zlib"]
        extra_incs = " ".join(f"-I{p}" for p in hdf5.cpp_info.includedirs)
        extra_libs = " ".join(f"-L{p}" for p in (hdf5.cpp_info.libdirs + zlib.cpp_info.libdirs))
        cflags = f"-O3 -Wall -Wextra -Wno-unused-result -fno-strict-aliasing {extra_incs} {extra_libs} -Wl,-rpath,$ORIGIN/../lib"
        for t in self._tools:
            self.run(
                f"make -C {self.source_folder} {t} CC={cc} PATH_HDF5={hdf5.package_folder} CFLAGS='{cflags}'",
                cwd=self.source_folder,
            )

    def package(self):
        for t in self._tools:
            copy(self, t, self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
