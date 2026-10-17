#!/usr/bin/env python3
"""Conan recipe — highway 1.3.0 (Google SIMD 库，鸿蒙 aarch64).

Highway 是 Google 开发的 SIMD 指令封装库，提供跨平台向量化运算接口。
鸿蒙 aarch64 下自动选用 NEON 指令路径。

构建系统：CMake
平台：OHOS aarch64 / Linux / macOS / Windows
依赖：零运行时依赖
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake


class HighwayConan(ConanFile):
    name = "highway"
    version = "1.3.0"
    description = "Google Highway — SIMD 向量化运算库（aarch64 NEON 路径自动选择）"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/highway"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    generators = "CMakeToolchain", "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # HWY_TEST_STANDALONE=ON：保留上游测试（规则5），但跳过 googletest 的
        # ExternalProject 下载（CMake 默认会从 github.com clone googletest，
        # CI 沙箱无法直连 github 导致构建失败）。standalone 模式使用 highway
        # 自带的轻量测试框架（hwy/tests/hwy_gtest.h 实现 GTest 兼容层）。
        cmake.configure(variables={
            "HWY_ENABLE_EXAMPLES": "OFF",
            "HWY_ENABLE_CONTRIB": "OFF",
            "HWY_TEST_STANDALONE": "ON",
        })
        cmake.build()

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "hwy"),
             os.path.join(self.package_folder, "include/hwy"))
        copy(self, "*.h", os.path.join(self.source_folder, "hwy/ops"),
             os.path.join(self.package_folder, "include/hwy/ops"))
        copy(self, "**/*.h", os.path.join(self.source_folder, "hwy/contrib"),
             os.path.join(self.package_folder, "include/hwy/contrib"))
        copy(self, "libhwy.*", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["hwy"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "hwy")
        self.cpp_info.set_property("cmake_target_name", "hwy::hwy")
        self.cpp_info.set_property("pkg_config_name", "libhwy")
