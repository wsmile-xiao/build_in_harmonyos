#!/usr/bin/env python3
"""Conan recipe — span-lite 0.11.0 (CMake header-only library).

span-lite 是 std::span 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SpanLiteConan(ConanFile):
    name = "span-lite"
    version = "0.11.0"
    description = "A C++20-like span for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/span-lite"
    url = ""  # CI fills this
    topics = ("span", "header-only", "cpp11", "cpp17", "cpp20")

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
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["SPAN_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["SPAN_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "span-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::span-lite")
        self.cpp_info.libs = []
