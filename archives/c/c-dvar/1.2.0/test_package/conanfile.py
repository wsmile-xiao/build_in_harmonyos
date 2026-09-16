#!/usr/bin/env python3
"""Conan test_package — c-dvar L1 消费者测试。

编译并真实调用 c-dvar API（类型解析/变体序列化往返/类型串比较）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CDvarTestConan(ConanFile):
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
        self.run("ctest --test-dir . --output-on-failure", cwd=self.build_folder)
