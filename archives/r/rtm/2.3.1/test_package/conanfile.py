#!/usr/bin/env python3
"""Conan test_package — rtm 2.3.1 (header-only, L1 test).

真实调用被测包 API（R34）：test.cpp include rtm/vector4f.h 与 rtm/scalarf.h，
执行向量加法并断言结果，CI 经 `conan create` 自动执行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RtmTestConan(ConanFile):
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
        # 实际运行测试二进制（L0d: 必须含 self.run，非空壳）
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_rtm")
        self.run(test_bin, env="conanrun")