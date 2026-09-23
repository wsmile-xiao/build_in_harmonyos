#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test.

libpgf 是纯库包，无命令行工具；本消费者程序调用 CPGFImage API 完成
64x48 RGB 图像的无损编码→内存流→解码往返，并逐字节断言一致性（R34）。

File location: archives/l/libpgf/7.21.7/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibPgfTestConan(ConanFile):
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
        # W3 L0d/R34：test() 必须 self.run 实际执行被测物，禁止空壳。
        # 直接运行编译出的消费者程序，以其退出码断言 5 项检查全部通过。
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libpgf")
        self.run(f'"{binary}"', env="conanrun")
