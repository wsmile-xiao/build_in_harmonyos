#!/usr/bin/env python3
"""Conan recipe for ankerl-unordered-dense 4.5.0 — header-only C++17 hashmap/hashset.

ankerl::unordered_dense::map / ankerl::unordered_dense::set are header-only
(CMake INTERFACE target `unordered_dense` with `cxx_std_17` compile feature).
No compilation is needed for the library itself; the recipe copies the single
public header `ankerl/unordered_dense.h` into the package include directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class AnkerlUnorderedDenseConan(ConanFile):
    name = "ankerl-unordered-dense"
    version = "4.5.0"
    description = "A fast & densely stored hashmap and hashset based on robin-hood backward shift deletion (header-only C++17)"
    license = "MIT"
    homepage = "https://github.com/martinus/unordered_dense"
    url = ""  # CI fills this
    topics = ("hashmap", "hashset", "robin-hood", "header-only")

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
        # Header-only: only the public header is installed (upstream CMakeLists
        # installs DIRECTORY include/ankerl -> ${CMAKE_INSTALL_INCLUDEDIR}).
        copy(
            self,
            "unordered_dense.h",
            src=os.path.join(self.source_folder, "include", "ankerl"),
            dst=os.path.join(self.package_folder, "include", "ankerl"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # Mirror the upstream CMake package name/target so consumers can use
        # find_package(unordered_dense) + unordered_dense::unordered_dense.
        self.cpp_info.set_property("cmake_file_name", "unordered_dense")
        self.cpp_info.set_property("cmake_target_name", "unordered_dense::unordered_dense")
        self.cpp_info.set_property("cmake_build_modules", [])
