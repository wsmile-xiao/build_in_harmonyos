#!/usr/bin/env python3
"""Conan test_package — generic_serialization 1.0.0 消费者验证.

真实调用 gs::serializer 完成一次序列化/反序列化往返并断言（R34）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GenericSerializationTestConan(ConanFile):
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
        # 直接运行二进制兜底
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_generic_serialization"), env="conanrun")
