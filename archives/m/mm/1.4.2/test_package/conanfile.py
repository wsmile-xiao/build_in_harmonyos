#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/mm/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MmTestConan(ConanFile):
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
        # CTest 驱动 CMakeLists.txt 中注册的 test_mm（10 条 CHECK 断言）
        cmake = CMake(self)
        cmake.test()
        # 再显式执行一次测试二进制：以进程退出码直接判定消费者测试结果，
        # 确保 test() 真实运行被测程序而非空壳（见 docs/ADAPTATION_GUIDE.md §5）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mm"), env="conanrun")
