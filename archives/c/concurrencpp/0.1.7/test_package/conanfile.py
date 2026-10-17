#!/usr/bin/env python3
"""test_package for concurrencpp 0.1.7 — verifies consumers can link and use the lib."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ConcurrencppTestConan(ConanFile):
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
        # 直接运行消费者测试二进制（L0d: test() 必须含 self.run 实质执行）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_concurrencpp"), env="conanrun")