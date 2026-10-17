#!/usr/bin/env python3
"""simde 0.8.2 consumer test：编译并运行 test.c，验证 simde 便携 SIMD API 可用。"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SimdeTestConan(ConanFile):
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
        # L0d: 显式运行 CMake 构建的 test_simde 消费者可执行文件（真实执行，非空壳）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_simde"), env="conanrun")