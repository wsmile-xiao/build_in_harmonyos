#!/usr/bin/env python3
"""Conan test package — npth 1.8.1 (L1 consumer test)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NpthTestConan(ConanFile):
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
        # Run the consumer binaries directly as well, so the package is not
        # only exercised through the CTest wrapper.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_npth"),
                 env="conanrun")
        # 鸿蒙特有测试（OHOS/musl 平台点）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_npth_ohos"),
                 env="conanrun")
