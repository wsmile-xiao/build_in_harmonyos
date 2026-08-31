#!/usr/bin/env python3
"""Conan test_package — cbehave 1.0.0 (L1 consumer test).

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CbehaveTestConan(ConanFile):
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
        # 实际运行消费者测试二进制（R34：实质依赖被测包；L0d：test() 含 self.run）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cbehave"), env="conanrun")