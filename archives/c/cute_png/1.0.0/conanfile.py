#!/usr/bin/env python3
"""Conan recipe — cute_png 1.0.0 (single-file header library).

cute_png is part of Randy Gaul's cute_headers collection. It is a
single-file C header implementing PNG load/save and texture-atlas
compilation, with a bundled DEFLATE-compliant decompressor and LZ77
compressor. Self-contained C/C++, no external dependencies, no
compilation needed.

Note on the 1.0.0 version carrier: upstream cute_headers publishes no
tag/release for the per-library headers, so 1.0.0 is anchored to the
internal revision history of the header — "1.0 (12/23/2016) initial
release" at upstream commit 35fb638f58db, when the file was named
tinydeflate.h (impl macro TINYDEFLATE_IMPL, API prefix td*). It was
renamed tinypng.h (2017-11-01) then cute_png.h (2018-05-21); the master
version uses CUTE_PNG_IMPLEMENTATION and cp_* prefix. For the 1.0.0
version carrier the implementation macro is TINYDEFLATE_IMPL.

Define TINYDEFLATE_IMPL (1.0.0 carrier) / CUTE_PNG_IMPLEMENTATION in
exactly one translation unit that includes the header to get the
function definitions.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class CutePngConan(ConanFile):
    name = "cute_png"
    version = "1.0.0"
    description = "Single-file C header for PNG load/save and texture atlas compilation"
    license = "Zlib OR Unlicense"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = "https://github.com/RandyGaul/cute_headers"
    topics = ("png", "image", "header-only", "c", "c-plus-plus", "atlas", "deflate")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # cute_png.h (1.0.0 anchor) is the single official file from the
        # cute_headers repo (committed as tinydeflate.h at the anchor commit).
        data = self.conan_data["sources"]["cute_png.h"]
        download(self, data["url"], os.path.join(self.source_folder, "cute_png.h"),
                 sha256=data["sha256"])
        apply_conandata_patches(self)

    def build(self):
        # Header-only: nothing to compile.
        pass

    def package(self):
        copy(self, "cute_png.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cute_png")
        self.cpp_info.set_property("cmake_target_name", "cute_png::cute_png")
        self.cpp_info.set_property("pkg_config_name", "cute_png")
