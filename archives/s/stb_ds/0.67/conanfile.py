#!/usr/bin/env python3
"""Conan recipe for stb_ds 0.67 — single-header library (header-only)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class StbdsConan(ConanFile):
    name = "stb_ds"
    version = "0.67"
    # Trigger CI worker reallocation
    description = "stb single-header dynamic data structure library: hash tables, sets, dynamic arrays"
    license = "MIT"
    url = "https://github.com/nothings/stb"
    homepage = "https://github.com/nothings/stb"
    topics = ("data-structures", "header-only", "hash-table")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def build(self):
        # header-only 库无需构建；保留补丁应用调用（patches 为空时无操作）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "stb_ds.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "stb_ds")
        self.cpp_info.set_property("cmake_target_name", "stb::ds")
        self.cpp_info.set_property("pkg_config_name", "stb_ds")
