#!/usr/bin/env python3
"""Conan test_package — libiec61850 1.6.1 消费者视角验证（Conan L1）。

CI 的 `conan create` 会在包构建完成后自动执行本 test_package：
编译消费者程序 → 链接已安装的 libiec61850 → 真实运行并核对断言。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Libiec61850TestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libiec61850")
            self.run(bin_path, env="conanrun")
