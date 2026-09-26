#!/usr/bin/env python3
"""Conan recipe — lurlparser 1.1 (lightweight URL & URI parser, RFC 1738/3986).

LUrlParser (github.com/corporateshark/LUrlParser, tag release-1.1) is a tiny
C++11 library: public header LUrlParser.h + one implementation file
LUrlParser.cpp.  Upstream CMakeLists only builds the Example executable and
has no install rules, so patch 0001 adds a STATIC library target, install
rules for the public header/license, and an optional WITH_TESTS gtest suite.
Patch 0002 ports the stale upstream test/test.cpp (which referenced the
removed clParseURL/m_* API) to the release-1.1 ParseURL/scheme_* API.

No third-party runtime dependencies (W0 verified); gtest is required only
when with_tests=True and comes from the ohpcd registry (gtest/1.17.0).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LurlparserConan(ConanFile):
    name = "lurlparser"
    version = "1.1"
    description = "Lightweight URL & URI parser (RFC 1738, RFC 3986) in C++11"
    license = "MIT"
    homepage = "https://github.com/corporateshark/LUrlParser"
    url = "https://github.com/corporateshark/LUrlParser"
    topics = ("url", "uri", "parser", "rfc3986", "rfc1738")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "with_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_tests:
            # gtest/1.17.0 已发布（W0 conan download 核实），仅上游测试需要
            self.requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 系统同名库静态；本库为通用静态库，默认静态
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake 4.x 兼容：上游 cmake_minimum_required(3.0) 在 CMake 4.1.2 下失败
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake 不识别 OHOS，注入 Linux 平台 + armv8 处理器
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
        tc.variables["WITH_TESTS"] = "ON" if self.options.with_tests else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests:
            # 上游测试：ctest 运行 8 个移植后的 TEST_F 用例（见 test/README.txt）
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["LUrlParser"]
        self.cpp_info.includedirs = ["include"]
        # 静态库；默认动态由 Conan 管理（R26 非系统同名库）
        self.cpp_info.bindirs = []
