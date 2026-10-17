#!/usr/bin/env python3
"""Conan test_package — micro-ecc 1.1.

L1 官方测试：消费者视角验证 libuecc 静态库可链接、可调用真实 ECDH/ECDSA API。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MicroEccTestConan(ConanFile):
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
        # 直接运行二进制作为兜底（CMake 测试失败时保留可追溯输出）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_micro_ecc"), env="conanrun")
