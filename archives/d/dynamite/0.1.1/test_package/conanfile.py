#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/dynamite/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DynamiteTestConan(ConanFile):
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
        # 直接运行测试二进制并注入 conanrun 环境（LD_LIBRARY_PATH 指向包
        # libdir），ctest 不注入该环境导致运行时 "Error loading shared library
        # libdynamite.so.0 / symbol not found"。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_dynamite"),
                 env="conanrun")
