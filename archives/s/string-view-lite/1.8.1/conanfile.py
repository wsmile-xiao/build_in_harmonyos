#!/usr/bin/env python3
"""Conan recipe — string-view-lite 1.8.1 (CMake header-only library).

string-view-lite 是 std::string_view 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
配方骨架沿用本仓已验证的 string-view-lite/1.8.0 配方与知识 E321
（martinmoene lite 系 header-only Conan 2.x 配方模式）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class StringViewLiteConan(ConanFile):
    name = "string-view-lite"
    version = "1.8.1"
    description = "A C++17-like string_view for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/string-view-lite"
    url = ""  # CI fills this
    topics = ("string-view", "header-only", "cpp11", "cpp17")

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
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["STRING_VIEW_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["STRING_VIEW_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "string-view-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::string-view-lite")
        self.cpp_info.libs = []
