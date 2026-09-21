#!/usr/bin/env python3
"""Conan test_package — b64.c 0.1.0 消费者验证。

ctest 运行 test.c（b64_encode + b64_decode_ex 往返断言），
并直接以运行时产物 test_b64.c 验证第三方使用者可编译、链接、
调用并正常运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class B64CTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_b64.c"), env="conanrun")