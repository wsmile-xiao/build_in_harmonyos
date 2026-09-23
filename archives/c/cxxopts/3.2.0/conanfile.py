#!/usr/bin/env python3
"""Conan recipe for cxxopts 3.2.0, a header-only C++ option parser."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CxxoptsConan(ConanFile):
    name = "cxxopts"
    version = "3.2.0"
    description = "Header-only C++ command line option parser"
    license = "MIT"
    homepage = "https://github.com/jarro2783/cxxopts"
    url = "https://github.com/jarro2783/cxxopts"

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
        tc.variables["CXXOPTS_BUILD_TESTS"] = "ON"
        tc.variables["CXXOPTS_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "CXXOPTS_BUILD_TESTS": "ON",
            "CXXOPTS_BUILD_EXAMPLES": "OFF",
        })
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cxxopts")
        self.cpp_info.set_property("cmake_target_name", "cxxopts::cxxopts")
        self.cpp_info.includedirs = ["include"]
