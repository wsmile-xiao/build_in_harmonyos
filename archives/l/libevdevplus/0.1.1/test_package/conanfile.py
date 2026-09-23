#!/usr/bin/env python3
"""Test package for libevdevplus 0.1.1 — Conan L1 official test.

用 Conan CMakeToolchain/CMakeDeps 交叉编译 test_libevdevplus.cpp 并链接被测包
（默认 cmake_file_name = 包名 → find_package(libevdevplus) +
libevdevplus::libevdevplus）。测试源实质调用库 API（R34）：InputEvent /
EventDeviceID / EventDevice::IsValidDevice / 库导出的 Table_* 键盘映射表。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibevdevplusTestConan(ConanFile):
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
        # 再直接运行一次二进制（R34：消费方视角的实质 API 测试；
        # 输出 checks=<N> failures=0 作为证据行）
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libevdevplus"),
            env="conanrun",
        )
