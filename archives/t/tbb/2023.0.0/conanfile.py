#!/usr/bin/env python3
"""Conan recipe — tbb (oneTBB) 2023.0.0

Rich and complete approach to parallelism in C++.
License: Apache-2.0
Homepage: https://uxlfoundation.github.io/oneTBB/
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TbbConan(ConanFile):
    name = "tbb"
    version = "2023.0.0"
    description = "Intel Threading Building Blocks (oneTBB) - Rich and complete approach to parallelism in C++"
    license = "Apache-2.0"
    homepage = "https://uxlfoundation.github.io/oneTBB/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # tbb is NOT a system same-name library → dynamic by default (R26 exempt)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["TBB_TEST"] = "OFF"
        tc.variables["TBB4PY_BUILD"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
        # Only expose the core tbb library for the test package
        # tbbmalloc and tbbmalloc_proxy are installed but not required
        # for basic parallel_for functionality
        self.cpp_info.set_property("cmake_file_name", "TBB")
        self.cpp_info.set_property("cmake_target_name", "tbb::tbb")
        self.cpp_info.libs = ["tbb"]
