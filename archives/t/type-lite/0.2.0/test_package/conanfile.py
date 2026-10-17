#!/usr/bin/env python3
"""Conan test_package — type-lite 0.2.0 消费者验证 (C++ header-only).

调用被测库 nonstd/type.hpp 的 API，验证强类型语义正确。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TypeLiteTestConan(ConanFile):
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
        # 直接运行二进制以确保真实执行
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_type_lite"), env="conanrun")