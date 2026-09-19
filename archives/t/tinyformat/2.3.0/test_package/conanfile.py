#!/usr/bin/env python3
"""Conan test_package — tinyformat 2.3.0 (header-only, L1 test).

消费者视角验证：#include <tinyformat.h> 真实编译链接并运行，
断言 tfm::format / tfm::printf 的核心 API 行为（R34：禁止空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TinyformatTestConan(ConanFile):
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
        # 直接运行测试二进制：断言 tfm::format 输出正确（非空壳）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tinyformat"), env="conanrun")
