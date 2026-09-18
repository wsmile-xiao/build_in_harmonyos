#!/usr/bin/env python3
"""Conan recipe — libfex 0.1.0 (CMake)

libfex: C++23 库，FUSE-over-io_uring 的 fusex 内核文件系统用户态对应端。
适配要点：
  - 上游 CMakeLists 要求 C++23（CMAKE_CXX_STANDARD 23）；OHOS clang-15 只认
    -std=c++2b（c++23 字面量非法），故显式传 -std=c++2b（含下游 cxxflags）。
  - 依赖 liburing（io_uring 传输层），由 Conan 管理（liburing/2.15）。
  - libc++15 缺 <expected>：patches 注入 fex/expected_compat.hpp polyfill，
    并把 5 处 #include <expected> 改指该头。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibfexConan(ConanFile):
    name = "libfex"
    version = "0.1.0"
    description = "libfex: modern C++ library for the fusex kernel filesystem (FUSE-over-io_uring userspace counterpart)"
    license = "BSD-2-Clause OR GPL-2.0-only"
    homepage = "https://github.com/hbirth/libfex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("liburing/2.15")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeDeps: 为 liburing 生成 liburingConfig.cmake / liburing::liburing 目标
        # （上游 CMakeLists 补丁改为 find_package(liburing CONFIG)）
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        # R33: 编译器/标志来自 Conan，不依赖裸 shell 环境变量
        # 注意：不在这里写 CMAKE_CXX_STANDARD=2b —— CMake 只认数值标准
        # （"2b" 会在 project() ABI 探测处报 "requires the language dialect CXX2b"）。
        # 上游 CMakeLists set(CMAKE_CXX_STANDARD 23) 由 CMake 对 clang-15 自动
        # 映射为 -std=c++2b（本地直编已验证 flags.make 含 -std=c++2b）。
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 库产物为 libfex（CMake target fex，OUTPUT_NAME fex）
        self.cpp_info.libs = ["fex"]
        # 下游也必须以 C++2b 消费公共头（公共 API 使用 std::expected 等 C++23 特性）
        if self.settings.compiler == "clang":
            self.cpp_info.cxxflags = ["-std=c++2b"]
