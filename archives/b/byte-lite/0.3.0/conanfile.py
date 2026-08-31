#!/usr/bin/env python3
"""Conan recipe — byte-lite 0.3.0 (CMake header-only library).

byte-lite 是 std::byte 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ByteLiteConan(ConanFile):
    name = "byte-lite"
    version = "0.3.0"
    description = "A single-file header-only C++17-like byte, a distinct type for raw memory access, for C++98, C++11 and later"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/byte-lite"
    url = ""  # CI fills this
    topics = ("byte", "header-only", "cpp11", "cpp17")

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
        tc.variables["BYTE_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["BYTE_LITE_OPT_BUILD_EXAMPLES"] = False
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
        self.cpp_info.set_property("cmake_file_name", "byte-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::byte-lite")
        self.cpp_info.libs = []
