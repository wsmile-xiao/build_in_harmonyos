#!/usr/bin/env python3
"""Conan recipe — ring-span-lite 0.7.0 (CMake header-only library).

ring-span-lite 是 std::ring_span 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class RingSpanLiteConan(ConanFile):
    name = "ring-span-lite"
    version = "0.7.0"
    description = "A C++98, C++11 and later ring_span type in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/ring-span-lite"
    url = ""  # CI fills this
    topics = ("ring-span", "ring", "header-only", "cpp98", "cpp11")

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
        # E092: CMake does not recognize OHOS as a target platform.
        # OHOS 的 Conan arch=armv8 不能直接作为 CMAKE_SYSTEM_PROCESSOR，需映射为 aarch64；
        # Linux 保留实际架构值（str(self.settings.arch)），避免 x86_64 等场景被错误覆盖。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["RING_SPAN_LITE_OPT_BUILD_TESTS"] = False
        tc.variables["RING_SPAN_LITE_OPT_BUILD_EXAMPLES"] = False
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
        self.cpp_info.set_property("cmake_file_name", "ring-span-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::ring-span-lite")
        self.cpp_info.libs = []