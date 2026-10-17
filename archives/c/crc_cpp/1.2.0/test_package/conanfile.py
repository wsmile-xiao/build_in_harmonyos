#!/usr/bin/env python3
"""Conan test_package — crc_cpp 1.2.0"""

import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CrcCppTestConan(ConanFile):
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
        # 实际执行两个测试二进制（L0d 要求 test() 内有 self.run，非空壳）
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_crc_cpp"), env="conanrun")
        self.run(os.path.join(bin_dir, "test_ohos_special"), env="conanrun")
