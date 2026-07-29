#!/usr/bin/env python3
"""Conan recipe for console_bridge 1.0.2 (CMake project).

console_bridge is a ROS-independent logging library that provides console
message output functionality. It is NOT a system same-name library, so it
defaults to shared linking (R26: only system same-name libraries must be static).

R32: settings.os judgment uses `in ("Linux", "OHOS")` not `== "Linux"`.
R33: Compiler is set by Conan profile [conf] tools.build:compiler_executables,
      no shell env var fallback.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ConsoleBridgeConan(ConanFile):
    name = "console_bridge"
    version = "1.0.2"
    description = "ROS-independent logging library providing console message output"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ros/console_bridge"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, build_folder="_build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # 启用上游测试 (test/console_TEST.cc, gtest 套件, 13 个 TEST 用例)
        # 补丁 0001 已移除 PythonInterp+wget 硬依赖 (lint 测试, 非功能测试)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 层 1: 上游官方测试 — 运行 gtest 套件 (console_TEST, 13 用例)
        # 失败则 conan create 失败 → 构建失败 (TEST_QUALITY_SPEC §3.1)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["console_bridge"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
