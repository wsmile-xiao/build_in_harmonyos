#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 mpdecimal (R34: 实质调用被测包 API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MpdecimalTestConan(ConanFile):
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
        # L0d: 显式运行消费者二进制（C API + C++ API 实质调用）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_mpdecimal")
        self.run(bin_path, env="conanrun")