#!/usr/bin/env python3
"""Conan test_package — charls 2.4.3 (JPEG-LS C++ library).

L1 test: compile a small C++ program that encodes and decodes a JPEG-LS image,
verifying lossless round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CharlsTestConan(ConanFile):
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
        # 运行测试二进制 — 成功返回 0
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_charls"), env="conanrun")
