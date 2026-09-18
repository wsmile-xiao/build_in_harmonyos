#!/usr/bin/env python3
"""Conan test_package — sexpp 0.9.1 L1 official test (PF3: self.run real execution)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SexppTestConan(ConanFile):
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
        # PF3: 必须通过 self.run 实际执行被测包构建出的消费者测试二进制，
        # 验证链接与运行（解析 S-表达式并经公开 API 回打）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sexpp"),
                 env="conanrun")
