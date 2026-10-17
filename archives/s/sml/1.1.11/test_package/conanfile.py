#!/usr/bin/env python3
"""Conan test_package — sml 1.1.11 L1 消费者测试.

R34: test_package 必须真实调用被测包 API — test.cpp 实际 include
<boost/sml.hpp> 并构建/运行状态机、断言迁移结果（非纯打印空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SmlTestConan(ConanFile):
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
        # L0d/R34: 实际运行测试二进制（消费者视角真实调用 sml API）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sml"), env="conanrun")