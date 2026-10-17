#!/usr/bin/env python3
"""Conan recipe — geojson-vt-cpp 6.6.5 (header-only C++14)."""

import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GeojsonVtCppConan(ConanFile):
    name = "geojson-vt-cpp"
    version = "6.6.5"
    description = "Port to C++ of JS GeoJSON-VT for slicing GeoJSON into vector tiles on the fly"
    license = "ISC"
    homepage = "https://github.com/mapbox/geojson-vt-cpp"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mapbox-geometry/2.0.3")
        self.requires("mapbox-variant/1.2.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译产物；仅应用 conandata 声明的补丁（当前为空）
        apply_conandata_patches(self)

    def package(self):
        include_src = os.path.join(self.source_folder, "include")
        copy(self, "*.hpp", src=include_src,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "geojson-vt-cpp")
        self.cpp_info.set_property("cmake_target_name", "mapbox::geojsonvt")