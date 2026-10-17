#!/usr/bin/env python3
"""Conan recipe for cxxopts 3.3.1.1, a header-only C++ option parser."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, export_conandata_patches


class CxxoptsConan(ConanFile):
    name = "cxxopts"
    version = "3.3.1.1"
    description = "Header-only C++ command line option parser"
    license = "MIT"
    homepage = "https://github.com/jarro2783/cxxopts"
    url = "https://github.com/jarro2783/cxxopts"

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
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CXXOPTS_BUILD_TESTS"] = "ON"
        tc.variables["CXXOPTS_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：ctest 运行 test/ 的 option_test（catch 单测）
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.components["cxxopts"].libs = []
        self.cpp_info.components["cxxopts"].includedirs = ["include"]
