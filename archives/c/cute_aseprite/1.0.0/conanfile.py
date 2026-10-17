#!/usr/bin/env python3
"""Conan recipe — cute_aseprite 1.0.0 (single-file header library).

cute_aseprite is part of Randy Gaul's cute_headers collection. It is a
single-file C header that parses .ase/.aseprite files into a compact struct
collection. The header is self-contained (embeds its own DEFLATE inflater);
no external dependencies, no compilation needed.

Define CUTE_ASEPRITE_IMPLEMENTATION in exactly one translation unit that
includes the header to get the function definitions.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class CuteAsepriteConan(ConanFile):
    name = "cute_aseprite"
    version = "1.0.0"
    description = "Single-file C header to parse .ase/.aseprite files"
    license = "Zlib OR Unlicense"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = "https://github.com/RandyGaul/cute_headers"
    topics = ("aseprite", "sprite", "header-only", "c", "c-plus-plus")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # cute_aseprite.h is a single official file from the cute_headers repo.
        data = self.conan_data["sources"]["cute_aseprite.h"]
        download(self, data["url"], os.path.join(self.source_folder, "cute_aseprite.h"),
                 sha256=data["sha256"])
        # R07: v1.00 header uses uint8_t/uint16_t/uint32_t in struct definitions
        # before including <stdint.h> (stdint.h only included in the impl
        # section). Patch adds the missing include before the structs.
        apply_conandata_patches(self)

    def build(self):
        # Header-only: nothing to compile.
        pass

    def package(self):
        copy(self, "cute_aseprite.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cute_aseprite")
        self.cpp_info.set_property("cmake_target_name", "cute_aseprite::cute_aseprite")
        self.cpp_info.set_property("pkg_config_name", "cute_aseprite")