#!/usr/bin/env python3
"""Conan test_package for gcem 1.16.0 — L1 官方测试。

验证 header-only 库 gcem 的头文件可被下游 C++ 程序包含，
且编译期 constexpr 数学函数可正常计算（消费方视角验证）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GcemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 直接执行测试二进制（避免纯框架桩）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_gcem"), env="conanrun")
        # 鸿蒙特有测试入口：验证 __OHOS__/__aarch64__ 平台宏 + gcem API 实测
        self.run(os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test"), env="conanrun")