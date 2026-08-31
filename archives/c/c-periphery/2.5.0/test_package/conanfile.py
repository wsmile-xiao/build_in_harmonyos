#!/usr/bin/env python3
"""Conan test_package — c-periphery 消费者验证（L1 官方测试）。

编译链接 libperiphery 并运行 test_periphery：version API 断言 +
serial 错误路径断言（不依赖真实外设硬件，CI 可复现）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CPeripheryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_periphery")
        self.run(f'"{bin_path}"', env="conanrun")
