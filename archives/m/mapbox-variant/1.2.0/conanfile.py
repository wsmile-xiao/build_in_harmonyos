#!/usr/bin/env python3
"""Conan recipe for Mapbox Variant 1.2.0 (header-only C++11/C++14)."""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class MapboxVariantConan(ConanFile):
    name = "mapbox-variant"
    version = "1.2.0"
    description = "Header-only alternative to boost::variant for C++11 and C++14"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mapbox/variant"
    topics = ("variant", "header-only", "c++11", "c++14")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        include_src = os.path.join(self.source_folder, "include")
        include_dst = os.path.join(self.package_folder, "include")
        copy(self, "*.hpp", src=include_src, dst=include_dst)
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "mapbox-variant")
        self.cpp_info.set_property("cmake_target_name", "mapbox::variant")
