#!/usr/bin/env python3
"""Conan test_package — cpputest 4.0_r2 (C/C++ unit testing framework).

L1 test: compile and run a small unit test written with cpputest,
verifying the framework's basic functionality (CHECK_EQUAL, STRCMP_EQUAL).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CppUTestTestConan(ConanFile):
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
        # 运行测试二进制 — 成功返回 0 (所有测试通过)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cpputest"), env="conanrun")
