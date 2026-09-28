#!/usr/bin/env python3
"""Conan test_package — veque 1.3.7 消费者视角真实用例（L1 / R34）."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VequeTestConan(ConanFile):
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
        # L0d/PF3：必须真实执行被测二进制；conan self.run 在 rc != 0 时抛错，
        # 因此 test.cpp 任一断言失败都会让本测试失败（非空壳、非 print-only）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_veque"), env="conanrun")
