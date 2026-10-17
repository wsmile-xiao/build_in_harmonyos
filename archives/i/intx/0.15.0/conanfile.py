#!/usr/bin/env python3
"""Conan recipe — intx 0.15.0 (CMake header-only multiprecision integer library).

intx 是 chfast 出的高性能任意精度整数 C++20 头文件库（INTERFACE target，无编译产物）。
header-only，无第三方运行时依赖；测试依赖 GTest（仅测试期）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class IntxConan(ConanFile):
    name = "intx"
    version = "0.15.0"
    description = "High-performance multiprecision integer library for C++"
    license = "Apache-2.0"
    homepage = "https://github.com/chfast/intx"
    url = ""  # CI fills this
    topics = ("integer", "multiprecision", "arbitrary-precision", "uint256", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # OHOS 工具链环境无 "Unix Makefiles" 默认生成器，Ninja 显式指定（E540）
        if self.settings.os == "OHOS":
            tc = CMakeToolchain(self, generator="Ninja")
        else:
            tc = CMakeToolchain(self)
        # E540/本机 conan helper 用相对路径解析 toolchain 会落到缓存构建根目录，
        # 显式用绝对路径覆盖 CMAKE_TOOLCHAIN_FILE，避免生成器子目录解析失败
        tc.cache_variables["CMAKE_TOOLCHAIN_FILE"] = os.path.join(
            self.generators_folder, "conan_toolchain.cmake")
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # intx 0.15.0 要求 C++20（std::unsigned_integral / std::countl_zero 等）
        # 移除 profile cppstd=17 的强制块，改由 cache_variables 显式指定 20
        tc.blocks.remove("cppstd")
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["INTX_TESTING"] = False
        tc.variables["INTX_INSTALL"] = True
        tc.variables["INTX_BENCHMARKING"] = False
        tc.variables["INTX_FUZZING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "INTX_TESTING": "OFF",
            "INTX_BENCHMARKING": "OFF",
            "INTX_INSTALL": "ON",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "intx")
        self.cpp_info.set_property("cmake_target_name", "intx::intx")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.components["intx"].set_property("cmake_target_name", "intx::intx")
