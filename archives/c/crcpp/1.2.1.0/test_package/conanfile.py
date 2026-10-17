#!/usr/bin/env python3
"""Conan test_package — crcpp 1.2.1.0 消费者测试（header-only 交付形态）。

消费者面真实使用 CRC API：
- include <CRC.h>（来自 conan 包 include/ 交付件）；
- CRC::Calculate / CRC::CalculateBits / CRC::Table 三条路径 + 版本宏自报；
- 13 条运行期断言，逐条打印读数，任一失败退出码非 0。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CrcppTestConan(ConanFile):
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
        # L0d 门禁：此处必须真实执行被测二进制（拒绝 echo/print/true 形态的空壳）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_crcpp")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
