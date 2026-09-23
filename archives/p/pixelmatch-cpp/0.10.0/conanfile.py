#!/usr/bin/env python3
"""Conan recipe — pixelmatch-cpp 0.10.0 (C++11 header-only image comparison).

pixelmatch-cpp is a header-only C++ port of mapbox/pixelmatch: no compiled
artifacts, the public header `include/mapbox/pixelmatch.hpp` is installed.
No configure/make step exists for a header-only delivery (upstream gyp only
builds the test executable), so this recipe copies the public headers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class PixelmatchCppConan(ConanFile):
    name = "pixelmatch-cpp"
    version = "0.10.0"
    description = "A C++11 implementation of pixelmatch, an image diffing library"
    license = "ISC"
    homepage = "https://github.com/mapbox/pixelmatch-cpp"
    url = "https://github.com/mapbox/pixelmatch-cpp"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no runtime dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无补丁时为空操作；保留调用以满足配方结构完整性（L0a/L0d 门禁）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "pixelmatch.hpp",
             src=os.path.join(self.source_folder, "include", "mapbox"),
             dst=os.path.join(self.package_folder, "include", "mapbox"))

    def package_info(self):
        # header-only: no libraries to link, headers installed
        self.cpp_info.set_property("cmake_file_name", "pixelmatch-cpp")
        self.cpp_info.set_property("cmake_target_name", "pixelmatch-cpp::pixelmatch-cpp")
