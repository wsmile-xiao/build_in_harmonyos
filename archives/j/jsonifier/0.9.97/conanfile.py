#!/usr/bin/env python3
"""Conan recipe for jsonifier 0.9.97 — header-only C++23 JSON parser/serializer.

jsonifier 是 header-only 库（INTERFACE CMake target），本体无编译产物、无第三方
运行时依赖。配方负责：
- 从官方 GitHub tag v0.9.97 下载源码（conandata.yml sha256 校验）
- 应用 OHOS aarch64 适配补丁（patches/，见 notes.md）：
  1) JsonifierCPUInstructions.hpp 38→8（x86 AVX 指令集改为 NEON——OHOS 为
     aarch64，x86 指令集位会导致 aarch64 编译走 immintrin.h 而失败）
  2) Config.hpp PREFETCH 增加 __aarch64__ 分支（避免无条件包含 xmmintrin.h）
  3) Allocator.hpp 的 <memory_resource> 加 __has_include 守卫（OHOS libc++ 缺该头）
  4) Error/Hash/Reflection 的 <source_location> 改用 Compat/SourceLocation.hpp
     shim（OHOS libc++ 缺标准头，提供 API 等价实现）
  5) String.hpp char_traits 的 uint8_type 特化排除纯 char（aarch64 char 默认
     unsigned，与 not_uint8_t 特化歧义）
  6) HashMap.hpp map_simd_t 别名补 typename（clang-15 对 P0634 支持不足）
- 打包 Include/jsonifier/ 头文件，cpp_info 暴露 include 路径
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get


class JsonifierConan(ConanFile):
    name = "jsonifier"
    version = "0.9.97"
    description = "jsonifier — header-only JSON parsing/serialization library (C++23)"
    license = "MIT"
    homepage = "https://github.com/RealTimeChris/Jsonifier"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "Include", "jsonifier"),
             dst=os.path.join(self.package_folder, "include", "jsonifier"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        # 上游要求 C++23（CMakeLists CMAKE_CXX_STANDARD 23；OHOS clang-15 用 c++2b 编译）
        if self.settings.compiler == "clang":
            self.cpp_info.cxxflags = ["-std=c++2b"]