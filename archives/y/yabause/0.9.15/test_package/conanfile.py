#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test (R34: 实质调用被测包 API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YabauseTestConan(ConanFile):
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
        # L0d: 必须 self.run 实际执行测试二进制（R34 实质验证）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_yabause"), env="conanrun")
