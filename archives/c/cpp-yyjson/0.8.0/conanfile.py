#!/usr/bin/env python3
"""Conan recipe — cpp-yyjson 0.8.0 (CMake, header-only C++20 JSON wrapper over yyjson).

cpp-yyjson 是基于 yyjson 的 header-only C++20 JSON 读写头文件库
（CMake INTERFACE target），依赖 yyjson/0.12.0 提供的 <yyjson.h>。
header-only：仅安装头文件与 CMake package config，不产生任何二进制。
上游测试 cpp_yyjson_test 通过 gtest 注册，recipe 内以选项开启后编译并实际运行。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class CppyyjsonConan(ConanFile):
    name = "cpp-yyjson"
    version = "0.8.0"
    description = "Ultra-fast and intuitive C++ JSON reader/writer with yyjson backend (header-only)"
    license = "MIT"
    homepage = "https://github.com/yosh-matsuda/cpp-yyjson"
    url = "https://github.com/yosh-matsuda/cpp-yyjson"
    topics = ("json", "yyjson", "header-only", "cpp20")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"build_tests": [True, False]}
    default_options = {"build_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cpp_yyjson.hpp 直接 #include <yyjson.h>，依赖已发布的 yyjson/0.12.0
        self.requires("yyjson/0.12.0")
        if self.options.build_tests:
            self.requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps 生成依赖(yyjson/gtest)的 CMake package config，
        # 上游 CMakeLists 用 find_package(yyjson CONFIG REQUIRED) 消费
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 OHOS 为目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # header-only 库：开启测试作为验证（默认 ON），benchmark 依赖 google-benchmark 不引入
        tc.variables["CPPYYJSON_BUILD_TEST"] = "ON" if self.options.build_tests else "OFF"
        tc.variables["CPPYYJSON_BUILD_BENCH"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试: test/CMakeLists.txt 用 gtest_discover_tests(PRE_TEST) 注册，
        # 构建后直接运行测试二进制获取实际执行证据。
        if self.options.build_tests:
            tests_bin = os.path.join(self.cpp.build.bindirs[0], "test", "cpp_yyjson_test")
            self.run(tests_bin, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游 CMake export 的 config 名/target 名均为 cpp_yyjson（PROJECT_NAME），
        # 与上游 install 的 cpp_yyjsonConfig.cmake / cpp_yyjson::cpp_yyjson 保持一致
        self.cpp_info.set_property("cmake_file_name", "cpp_yyjson")
        self.cpp_info.set_property("cmake_target_name", "cpp_yyjson::cpp_yyjson")
        self.cpp_info.libs = []