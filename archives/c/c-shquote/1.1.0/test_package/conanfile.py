#!/usr/bin/env python3
"""Conan test_package — c-shquote L1 消费者测试。

编译并真实调用 c-shquote 的 quote/unquote API，断言与上游 test-basic
一致的行为（引号包裹与去引号的往返结果）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CShquoteTestConan(ConanFile):
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
