#!/usr/bin/env python3
"""Conan test_package — corrade 2020.06 消费者验证 (鸿蒙专项)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CorradeTestConan(ConanFile):
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
        # 直接运行鸿蒙专项消费者测试二进制, 验证链接与 API 可用性
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_corrade"), env="conanrun")
