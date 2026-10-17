#!/usr/bin/env python3
"""Conan test_package — ee 3.2.2.

L1 官方测试：消费者视角验证 libee.a 可链接、可调用真实 EEPROM 模拟 API。
R34：test() 实际执行被测库 API，拒绝空壳。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EeTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ee"), env="conanrun")