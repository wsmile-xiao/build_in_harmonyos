#!/usr/bin/env python3
"""Conan recipe — any-lite 0.3.0.1 (CMake header-only library, upstream 0.3.0).

any-lite 是 std::any 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AnyLiteConan(ConanFile):
    name = "any-lite"
    version = "0.3.0.1"
    description = "A single-file header-only C++17-like any, a type-safe container for single values of any type for C++98, C++11 and later"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/any-lite"
    url = ""  # CI fills this
    topics = ("any", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["ANY_LITE_OPT_BUILD_TESTS"] = True
        tc.cache_variables["ANY_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.user_presets_path = False
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
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "any-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::any-lite")
        self.cpp_info.libs = []
