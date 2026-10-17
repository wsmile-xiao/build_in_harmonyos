#!/usr/bin/env python3
"""Conan test_package for etl 20.38.4 — L1 官方测试。

验证 header-only 库 etl 的头文件可被下游 C++ 程序包含，
且容器/算法在编译期与运行期均可正常使用（消费方视角验证）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EtlTestConan(ConanFile):
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
        # 直接运行测试二进制（L0d: 需 self.run 实际调用被测包二进制，R34 真实消费）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_etl"), env="conanrun")
