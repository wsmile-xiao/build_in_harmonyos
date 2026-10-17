#!/usr/bin/env python3
"""Conan test_package — compile-time-regular 3.11.0 L1 冒烟测试."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CompileTimeRegularTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁：test() 需显式 self.run() 执行构建产物
        # （cmake.test() 之外显式运行一次，验证二进制可执行）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ctre"), env="conanrun")
