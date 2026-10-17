#!/usr/bin/env python3
"""Conan test_package — gd 2.3.3 消费者验证 (L1).

真实调用 GD API：gdVersionString + gdImageCreateTrueColor + 绘图。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GdTestConan(ConanFile):
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
        # L0d/R34: 直接运行测试二进制（真实调用 GD API）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_gd"), env="conanrun")
