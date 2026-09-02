#!/usr/bin/env python3
"""Conan recipe for cpp-peglib 1.17.0 (C++17 header-only PEG library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


required_conan_version = ">=2.0"


class CppPeglibConan(ConanFile):
    name = "cpp-peglib"
    version = "1.17.0"
    package_type = "header-library"

    description = "A single-file C++17 header-only PEG parsing library"
    homepage = "https://yhirose.github.io/cpp-peglib/"
    license = "MIT"
    url = "https://github.com/yhirose/cpp-peglib"
    topics = ("parser", "peg", "header-only", "cpp17")

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.variables["BUILD_TESTS"] = True
        tc.variables["PEGLIB_BUILD_BENCHMARK"] = False
        tc.variables["PEGLIB_BUILD_EXAMPLES"] = False
        tc.variables["PEGLIB_BUILD_LINT"] = False
        tc.variables["PEGLIB_BUILD_PL0"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official tests: one GoogleTest executable discovered as
        # individual CTest cases by gtest_discover_tests().
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cpp-peglib")
        self.cpp_info.set_property("cmake_target_name", "cpp-peglib::cpp-peglib")

    def package_id(self):
        # The package contains only a source header and is independent of the
        # host compiler, build type, and architecture.
        self.info.clear()
