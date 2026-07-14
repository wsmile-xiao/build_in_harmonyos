#!/usr/bin/env python3
"""Conan test_package — libkeccak 1.4.3 L1 test.

R34: 测试实质调用 libkeccak API（SHA3-256 标准向量 + HMAC-SHA3-256）。
用 CMake（CMakeDeps + CMakeToolchain）取编译器，不裸用 shell 环境变量（R33）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkeccakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(test_bin, env="conanrun")
