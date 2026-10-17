#!/usr/bin/env python3
"""Conan recipe for jc_voronoi 0.9.0 — header-only C99 2D Voronoi diagram generator.

jc_voronoi is an stb-style single-header C library. The implementation is
instantiated in the consumer's translation unit by defining
JC_VORONOI_IMPLEMENTATION before including jc_voronoi.h (and optionally
JC_VORONOI_CLIP_IMPLEMENTATION for jc_voronoi_clip.h). No compilation is
needed for the library itself.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class JcVoronoiConan(ConanFile):
    name = "jc_voronoi"
    version = "0.9.0"
    description = "A fast C/C++ header only implementation for creating 2D Voronoi diagrams from a point set"
    license = "MIT"
    homepage = "https://github.com/JCash/voronoi"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "jc_voronoi.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "jc_voronoi_clip.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "jc_voronoi")
        self.cpp_info.set_property("cmake_target_name", "jc_voronoi::jc_voronoi")
