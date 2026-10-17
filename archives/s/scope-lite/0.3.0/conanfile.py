#!/usr/bin/env python3
"""Conan recipe — scope-lite 0.3.0 (CMake header-only library).

scope-lite 是 std::scope / std::scope_exit 等 RAII scope guard 的 C++98/11/14/17/20
单文件头文件回移库（nonstd 系列，作者 Martin Moene）。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScopeLiteConan(ConanFile):
    name = "scope-lite"
    version = "0.3.0"
    description = "A C++17-like std::scope for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/scope-lite"
    url = ""  # CI fills this
    topics = ("scope", "raii", "header-only", "cpp98", "cpp11")

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
        tc.variables["SCOPE_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["SCOPE_LITE_OPT_BUILD_EXAMPLES"] = False
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
        self.cpp_info.set_property("cmake_file_name", "scope-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::scope-lite")
        self.cpp_info.libs = []
