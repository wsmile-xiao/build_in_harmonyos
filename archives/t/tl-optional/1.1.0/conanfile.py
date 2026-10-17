#!/usr/bin/env python3
"""Conan recipe — tl-optional 1.1.0 (CMake header-only library).

tl-optional 是 std::optional 的 C++11/14/17 单头文件实现库（TartanLlama/optional）。
header-only（CMake INTERFACE library，导出 target tl::optional），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TlOptionalConan(ConanFile):
    name = "tl-optional"
    version = "1.1.0"
    description = "A C++11/14/17 std::optional implementation with functional-style extensions and reference support"
    license = "CC0-1.0"
    homepage = "https://github.com/TartanLlama/optional"
    url = ""  # CI fills this
    topics = ("optional", "header-only", "cpp11", "cpp14", "cpp17", "tartanllama")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["OPTIONAL_BUILD_TESTS"] = True
        tc.variables["OPTIONAL_BUILD_PACKAGE"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # 本包无补丁，no-op
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tl-optional")
        self.cpp_info.set_property("cmake_target_name", "tl::optional")
        self.cpp_info.libs = []
