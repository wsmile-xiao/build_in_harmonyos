#!/usr/bin/env python3
"""Conan recipe — cpp-sort 2.2.0 (CMake header-only library).

cpp-sort 是 header-only 的 C++17 排序算法库（INTERFACE library），
无任何第三方运行时依赖。使用上游自带 CMake 安装规则打包头文件与
CMake 包配置。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CppSortConan(ConanFile):
    name = "cpp-sort"
    version = "2.2.0"
    description = "Sorting algorithms & related tools, a header-only C++17 library"
    license = "MIT"
    homepage = "https://github.com/Morwenn/cpp-sort"
    url = ""  # CI fills this
    topics = ("cpp-sort", "sorting", "algorithms", "header-only", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CPPSORT_BUILD_TESTING"] = "OFF"
        tc.variables["CPPSORT_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpp-sort")
        self.cpp_info.set_property("cmake_target_name", "cpp-sort::cpp-sort")
        self.cpp_info.libs = []
