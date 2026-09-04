#!/usr/bin/env python3
"""Conan recipe — boolean-lite 0.1.0 (CMake header-only library).

boolean-lite 是 Martin Moene nonstd-lite 系列的强布尔类型（strong boolean）
单文件头文件库，C++98/11/14/17 通用，无任何第三方依赖。
header-only（CMake INTERFACE library）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BooleanliteConan(ConanFile):
    name = "boolean-lite"
    version = "0.1.0"
    description = "A strong boolean type for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/boolean-lite"
    url = ""  # CI fills this
    topics = ("boolean", "header-only", "cpp11", "cpp17")

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
        tc.variables["BOOLEAN_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["BOOLEAN_LITE_OPT_BUILD_EXAMPLES"] = False
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
        self.cpp_info.set_property("cmake_file_name", "boolean-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::boolean-lite")
        self.cpp_info.libs = []