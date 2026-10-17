#!/usr/bin/env python3
"""Conan recipe for json_struct 1.0.2.

json_struct is a single-header-only-ish C++20 library (headers live under
include/json_struct/).  The upstream CMake project exposes an INTERFACE
target `json_struct::json_struct` plus a pkg-config file.  No compiled
libraries are produced, so the package ships headers + CMake config only.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class JsonstructConan(ConanFile):
    name = "json_struct"
    version = "1.0.2"
    description = (
        "A library for parsing JSON directly to C++ structs and vice versa"
    )
    license = "MIT"
    homepage = "https://github.com/jorgen/json_struct"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only INTERFACE library: tests/examples/benchmarks off,
        # install the CMake package config so consumers can
        # find_package(json_struct).
        tc.variables["JSON_STRUCT_OPT_BUILD_TESTS"] = "OFF"
        tc.variables["JSON_STRUCT_OPT_BUILD_EXAMPLES"] = "OFF"
        tc.variables["JSON_STRUCT_OPT_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["JSON_STRUCT_OPT_INSTALL"] = "ON"
        tc.variables["JSON_STRUCT_OPT_DISABLE_PCH"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "json_struct")
        self.cpp_info.set_property("cmake_target_name", "json_struct::json_struct")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only: consumers only need the include directory.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "json_struct")