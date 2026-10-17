#!/usr/bin/env python3
"""Conan recipe — function2 4.2.3 (CMake, header-only).

function2 is a header-only C++ library providing improved drop-in
replacements for std::function (fu2::function, fu2::unique_function,
fu2::function_view).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Function2Conan(ConanFile):
    name = "function2"
    version = "4.2.3"
    description = "Improved and configurable drop-in replacement to std::function"
    license = "BSL-1.0"
    homepage = "https://github.com/Naios/function2"
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
        # 上游 tests 依赖 googletest submodule（tarball 不含 submodule 内容）；
        # function2 为 header-only，test_package 消费者测试已覆盖，无需跑上游 tests.
        tc.variables["BUILD_TESTING"] = "OFF"
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
