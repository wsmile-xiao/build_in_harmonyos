#!/usr/bin/env python3
"""Conan recipe — libflathashmap 0.0-git20180715.2c46874 (header-only)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibflathashmapConan(ConanFile):
    name = "libflathashmap"
    version = "0.0-git20180715.2c46874"
    description = "Very fast header-only C++ hash map and hash set implementations"
    license = "BSL-1.0"
    homepage = "https://github.com/skarupke/flat_hash_map"
    url = "https://github.com/skarupke/flat_hash_map"
    topics = ("hash-map", "hash-set", "header-only", "cpp14")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "*.hpp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libflathashmap")
        self.cpp_info.set_property(
            "cmake_target_name", "libflathashmap::libflathashmap"
        )
