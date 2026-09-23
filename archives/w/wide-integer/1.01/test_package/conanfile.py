#!/usr/bin/env python3
"""Conan test_package — wide-integer 1.01（header-only，L1 消费者验证）。

消费者视角：通过 CMakeDeps 引入 wide-integer 包，编译 test_wide_integer 并在
test() 中以 self.run() 真实运行该二进制，实际调用 uintwide_t 公开 API
（512 位乘法/除法/取模回环 + 十进制字符串交叉校验），满足 R34（禁止空壳测试）
与 CI L0d（test() 必须有 self.run() 调用）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WideintegerTestConan(ConanFile):
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
        # L0d：test() 必须包含真实 self.run() 调用，直接运行编译产物中的测试二进制。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_wide_integer"), env="conanrun")
