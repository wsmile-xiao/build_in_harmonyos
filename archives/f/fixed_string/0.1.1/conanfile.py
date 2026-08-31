#!/usr/bin/env python3
"""Conan recipe — fixed_string 0.1.1 (header-only C++17).

Upstream: https://github.com/unterumarmung/fixed_string
CMake exposes an INTERFACE library target `fixed_string` (no compile).
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMakeToolchain, cmake_layout


class FixedStringConan(ConanFile):
    name = "fixed_string"
    version = "0.1.1"
    description = "C++ library providing a basic_fixed_string template combining std::array fixed-size and std::string semantics"
    license = "MIT"
    homepage = "https://github.com/unterumarmung/fixed_string"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only: do not build tests/examples by default
        tc.variables["FIXED_STRING_OPT_BUILD_TESTS"] = "OFF"
        tc.variables["FIXED_STRING_OPT_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "include/*.hpp", self.source_folder, self.package_folder)
        copy(self, "LICENSE", self.source_folder, self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fixed_string")
        self.cpp_info.set_property("cmake_target_name", "fixed_string::fixed_string")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
