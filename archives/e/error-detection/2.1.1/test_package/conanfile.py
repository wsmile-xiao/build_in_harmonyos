#!/usr/bin/env python3
"""Conan test_package — error-detection 2.1.1 consumer test.

Verifies a third-party consumer can include err.h, link against
liberror-detection and call the public checksum/CRC APIs with observable
results (CRC-8/MAXIM and CRC-16/CCITT check values).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ErrorDetectionTestConan(ConanFile):
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
        cmake.build()
        # L0d 门禁要求 test() 内实际 self.run 执行测试二进制
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_error_detection"),
                 env="conanrun")
