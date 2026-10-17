#!/usr/bin/env python3
"""Conan test_package — libtnt 1.2.6 L1 冒烟测试."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibTntTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # TNT 为 C++98 时代模板库，CI profile 口径 cppstd=17 实测兼容
        # （C++98~17 全系均可编译，此处与 profile 对齐）
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁：test() 需显式 self.run() 执行构建产物
        # （cmake.test() 之外显式运行一次，验证二进制可执行）
        bindir = self.cpp.build.bindirs[0]
        # 组件冒烟（32 项断言）
        self.run(os.path.join(bindir, "test_libtnt"), env="conanrun")
        # 消费者用例（6 项断言：马尔可夫稳态幂迭代 + 加权平均）
        self.run(os.path.join(bindir, "test_consumer"), env="conanrun")
        # 鸿蒙特有测试（6 项断言：musl clock() 时钟路径 + 真机堆跨页
        # 大数组 + aarch64 FPU 浮点语义）
        self.run(os.path.join(bindir, "test_ohos"), env="conanrun")
