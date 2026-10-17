#!/usr/bin/env python3
"""Conan test_package — Unity 2.7.0 L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UnityTestConan(ConanFile):
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
        self.run(os.path.join(self.build_folder, "test_unity"), env="conanbuild")
        # 鸿蒙特有测试：版本头身份 + 核心断言 + double 断言 + 输出钩子（4 用例）
        self.run(os.path.join(self.build_folder, "test_unity_ohos"), env="conanbuild")
