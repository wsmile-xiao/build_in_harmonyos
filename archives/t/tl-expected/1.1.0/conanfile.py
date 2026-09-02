#!/usr/bin/env python3
"""Conan recipe — tl-expected 1.1.0 (CMake header-only library).

tl-expected 是 std::expected 的单文件头文件库（C++11/14/17，functional 扩展）。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class TlExpectedConan(ConanFile):
    name = "tl-expected"
    version = "1.1.0"
    description = "Single header implementation of std::expected with functional-style extensions"
    license = "CC0-1.0"
    homepage = "https://tl.tartanllama.xyz"
    url = ""  # CI fills this
    topics = ("expected", "header-only", "cpp17", "cpp14", "cpp11")

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
        # E092: CMake 不识别 OHOS 为目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["EXPECTED_BUILD_TESTS"] = False
        tc.variables["EXPECTED_BUILD_PACKAGE"] = True
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
        self.cpp_info.set_property("cmake_file_name", "tl-expected")
        self.cpp_info.set_property("cmake_target_name", "tl::expected")
        self.cpp_info.libs = []
