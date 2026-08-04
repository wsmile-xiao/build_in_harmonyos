#!/usr/bin/env python3
"""Conan recipe — tl (tl-expected) 1.3.1, header-only C++ library (CMake project).

Header-only: no build step, headers are copied into the package.
CMake package name: tl-expected, imported target: tl::expected (upstream).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TlConan(ConanFile):
    name = "tl"
    version = "1.3.1"
    description = "C++11/14/17 std::expected with functional-style extensions (tl::expected)"
    license = "CC0-1.0"
    homepage = "https://tl.tartanllama.xyz"
    url = ""
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "tl"),
             dst=os.path.join(self.package_folder, "include", "tl"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tl-expected")
        self.cpp_info.set_property("cmake_target_name", "tl::expected")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
