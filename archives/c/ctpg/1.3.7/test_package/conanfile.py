#!/usr/bin/env python3
"""Conan test_package — ctpg 1.3.7 消费者验证（R34: 真实调用被测包 API）.

使用 CTPG 编译期解析器生成器定义一个小型表达式解析器，解析 "1,2,3"
与编译期 "4,5"，断言值 6/9，验证头文件在 OHOS 目标上实际可编译可运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CtpgTestConan(ConanFile):
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
        # 直接运行消费者测试二进制（内部为 assert 断言：运行期 1,2,3=6、
        # 编译期 4,5=9——真实调用 CTPG 解析器 API，非空壳）
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ctpg")
        self.run(test_bin, env="conanrun")
