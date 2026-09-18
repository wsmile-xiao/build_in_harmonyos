#!/usr/bin/env python3
"""Conan test_package — libei 1.5.0 消费者测试（L1 official test）。

CI 在 conan create 时自动执行。C 消费者程序真实链接 libei.so +
libeis.so 并调用公共 API（上下文生命周期/模式判定/user_data 语义）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
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
        # 直接执行消费者测试二进制（输出 PASS/FAIL 与断言计数）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libei")
        self.run(f'"{exe}"', env="conanrun")
