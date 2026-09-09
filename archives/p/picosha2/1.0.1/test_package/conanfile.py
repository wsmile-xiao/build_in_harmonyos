#!/usr/bin/env python3
"""Conan test_package — picosha2 1.0.1 (header-only consumer test, R34)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Picosha2TestConan(ConanFile):
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
        # 真实执行消费者测试二进制（断言已知 SHA-256 向量，R34/L0d）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_picosha2"), env="conanrun")
