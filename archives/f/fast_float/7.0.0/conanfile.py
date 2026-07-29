#!/usr/bin/env python3
"""Conan recipe — fast_float 7.0.0 (CMake, header-only).

fast_float is a header-only C++ library for fast floating-point parsing.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FastfloatConan(ConanFile):
    name = "fast_float"
    version = "7.0.0"
    description = "Header-only C++ library for fast floating-point parsing"
    license = "Apache-2.0 OR MIT OR BSL-1.0"
    homepage = "https://github.com/fastfloat/fast_float"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 禁用上游 tests：tests/CMakeLists.txt:30 用 FetchContent_Populate(doctest) 从 github clone，
        # CI worker 网络禁 GitHub 报 'Couldn't connect to server'. fast_float header-only，
        # test_package 已自带消费者测试覆盖，无需跑上游 tests.
        tc.variables["FASTFLOAT_TEST"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = []
