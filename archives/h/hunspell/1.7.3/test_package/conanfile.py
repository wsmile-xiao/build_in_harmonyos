#!/usr/bin/env python3
"""Conan test_package — hunspell 1.7.3 消费者测试（R34）。

编译一个小 C++ 程序链接 libhunspell-1.7，加载内置迷你词典
(test.aff + test.dic)，真实执行 spell() 校验命中/未命中。
test() 直接 self.run 编译产物（门禁 R34 要求 test() 内显式 self.run，
不可仅靠 cmake.test()/ctest 兜底）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HunspellTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_hunspell")
        self.run(test_bin, env="conanrun")
