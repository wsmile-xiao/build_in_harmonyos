#!/usr/bin/env python3
"""json11 1.0.0 test_package — 消费者验证。

查找/链接 json11::json11，编译运行 test.cpp（实际调用 json11 C++ API 并断言）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Json11TestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_json11"), env="conanrun")
