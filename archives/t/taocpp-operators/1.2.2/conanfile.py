#!/usr/bin/env python3
"""Conan recipe for taocpp-operators 1.2.2 (CMake)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TaocppOperatorsConan(ConanFile):
    name = "taocpp-operators"
    version = "1.2.2"
    description = "C++11 single-header library providing efficient arithmetic operators"
    license = "MIT"
    homepage = "https://github.com/taocpp/operators"
    url = "https://github.com/taocpp/operators"

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
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["TAOCPP_OPERATORS_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "TAOCPP_OPERATORS_BUILD_TESTS": "ON",
        })
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "taocpp-operators")
        self.cpp_info.set_property("cmake_target_name", "taocpp-operators::taocpp-operators")
        self.cpp_info.includedirs = ["include"]
