#!/usr/bin/env python3
"""Conan recipe — cute_c2 1.0.0 (single-file header library).

cute_c2 is part of Randy Gaul's cute_headers collection. It is a
single-file C header implementing 2D collision detection routines
(circles, capsules, AABBs, rays, convex polygons), with optional
manifold generation, GJK, TOI and convex-hull support. Self-contained
C99, no external dependencies, no compilation needed.

Define CUTE_C2_IMPLEMENTATION in exactly one translation unit that
includes the header to get the function definitions.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class CuteC2Conan(ConanFile):
    name = "cute_c2"
    version = "1.0.0"
    description = "Single-file C header for 2D collision detection"
    license = "Zlib OR Unlicense"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = "https://github.com/RandyGaul/cute_headers"
    topics = ("collision", "2d", "header-only", "c", "c-plus-plus", "gjk", "physics")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # cute_c2.h (1.0.0 anchor) is the single official file from the
        # cute_headers repo (committed as tinyc2.h at the anchor commit).
        data = self.conan_data["sources"]["cute_c2.h"]
        download(self, data["url"], os.path.join(self.source_folder, "cute_c2.h"),
                 sha256=data["sha256"])
        # v1.0 header: C99 compat patch (missing <stdbool.h>/<string.h>,
        # compound-literal casts for C2_PLANE_AT and *h assignment).
        apply_conandata_patches(self)

    def build(self):
        # Header-only: nothing to compile.
        pass

    def package(self):
        copy(self, "cute_c2.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cute_c2")
        self.cpp_info.set_property("cmake_target_name", "cute_c2::cute_c2")
        self.cpp_info.set_property("pkg_config_name", "cute_c2")
