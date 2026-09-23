#!/usr/bin/env python3
"""Conan recipe — icecream-cpp 1.0.0 (CMake, header-only).

icecream-cpp is a single-header C++ library providing printf-style
debugging via the IC() macro.  Upstream build system is CMake with an
INTERFACE (header-only) target; install rules ship icecream.hpp plus a
CMake package config.  No runtime or build-time dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IcecreamCppConan(ConanFile):
    name = "icecream-cpp"
    version = "1.0.0"
    description = "C++ single-header printf-style debugging library (IC())"
    license = "MIT"
    homepage = "https://github.com/renatoGarcia/icecream-cpp"
    url = "https://github.com/renatoGarcia/icecream-cpp"

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
        # 上游 tests/ 依赖 Catch2/Boost/fmt 未发布到 ohpcd 制品仓，且头文件库
        # 无编译产物；消费者验证由 test_package 承担（R34 实质调用），
        # 故关闭上游 BUILD_TESTING，避免 conan create 时 find_package(Catch2) 失败。
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
