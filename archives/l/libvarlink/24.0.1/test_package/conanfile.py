#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libvarlink/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvarlinkTestConan(ConanFile):
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
        # 直接运行二进制（env="conanrun" 注入包 lib 加载路径；cmake.test()
        # 在 OHOS 上不带运行期 LD_LIBRARY_PATH 导致 "symbol not found"）
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_libvarlink"), env="conanrun")
