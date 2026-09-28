#!/usr/bin/env python3
"""Conan recipe for graphthewy 1.1, a header-only C++20 graph modelling library."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GraphthewyConan(ConanFile):
    name = "graphthewy"
    version = "1.1"
    description = "Header-only C++20 library for graph modelling and cycle detection"
    license = "EUPL-1.2"
    homepage = "https://github.com/alex-87/graphthewy"
    url = "https://github.com/alex-87/graphthewy"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["GRAPHTHEWY_BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "GRAPHTHEWY_BUILD_TESTS": "OFF",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "graphthewy")
        self.cpp_info.set_property("cmake_target_name", "graphthewy::graphthewy")
        self.cpp_info.includedirs = ["include"]