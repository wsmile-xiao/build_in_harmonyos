#!/usr/bin/env python3
"""Conan recipe — fast_float 8.0.1 (CMake, header-only).

fast_float is a header-only C++ library for fast floating-point parsing.
libcifpp v9.0.6 requires FastFloat 8.0 (find_package(FastFloat 8.0)).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FastfloatConan(ConanFile):
    name = "fast_float"
    version = "8.0.1"
    description = "Header-only C++ library for fast floating-point parsing"
    license = "Apache-2.0 OR MIT OR BSL-1.0"
    homepage = "https://github.com/fastfloat/fast_float"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # 禁用上游 tests：tests/CMakeLists.txt 用 FetchContent 从 GitHub 拉 doctest
        # 与 supplemental_test_files，CI worker 网络禁 GitHub。fast_float 为
        # header-only，test_package 已含消费者测试，无需跑上游 tests。
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
