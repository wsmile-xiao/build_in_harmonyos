#!/usr/bin/env python3
"""Conan test_package — xenium 0.0.2 (header-only, CMake 消费者)

以 CMake + CMakeDeps 消费 xenium::xenium 目标，编译并运行真实并发测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XeniumTestConan(ConanFile):
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
        # 直接运行二进制，以真实退出码判定结果（非零 = 有断言失败）。
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_xenium")
        self.run(f'"{bin_path}"', env="conanrun")
