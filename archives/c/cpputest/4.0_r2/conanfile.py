#!/usr/bin/env python3
"""Conan recipe — cpputest 4.0_r2 (CMake C/C++ unit testing framework).

cpputest 是 C/C++ 单元测试框架, 使用 CMake 构建,
生成 CppUTest (主库) + CppUTestExt (扩展库) 两个静态库。
无第三方依赖。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CppUTestConan(ConanFile):
    name = "cpputest"
    version = "4.0_r2"
    description = "C/C++ 单元测试框架, 支持内存泄漏检测和测试桩"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cpputest/cpputest"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "extensions": [True, False],
        "memory_leak_detection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "extensions": True,
        "memory_leak_detection": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 修复 cmake_minimum_required(VERSION 3.1) 与新版 CMake 的兼容性
        # 新版 CMake 移除了对 < 3.5 的兼容性支持, 需显式指定策略版本下限
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R26: 默认静态库
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 禁用测试和示例, 加速构建
        tc.variables["TESTS"] = "OFF"
        tc.variables["EXAMPLES"] = "OFF"
        # 扩展库和内存泄漏检测
        tc.variables["EXTENSIONS"] = "ON" if self.options.extensions else "OFF"
        tc.variables["MEMORY_LEAK_DETECTION"] = "ON" if self.options.memory_leak_detection else "OFF"
        # 其他选项
        tc.variables["C++11"] = "ON"
        tc.variables["VERBOSE_CONFIG"] = "OFF"
        tc.generate()

        # 修复编译器路径: profile 中的路径在本地可能不存在
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            content = re.sub(
                r'set\(CMAKE_C_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 设置 cmake 属性, 使 CMakeDeps 生成与上游命名一致的 target
        # find_package(CppUTest) → CppUTest::CppUTest, CppUTest::CppUTestExt
        self.cpp_info.set_property("cmake_file_name", "CppUTest")
        self.cpp_info.set_property("cmake_target_name", "CppUTest::CppUTest")
        self.cpp_info.libs = ["CppUTest"]
        if self.options.extensions:
            self.cpp_info.libs.append("CppUTestExt")
