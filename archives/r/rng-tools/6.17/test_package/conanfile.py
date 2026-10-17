#!/usr/bin/env python3
"""Conan test_package — rng-tools 6.17 消费者测试（L1）。

rng-tools 是纯可执行文件包（rngd/rngtest），测试程序只编译自身、
通过 conanrun 环境的 PATH 真实调用被测二进制并断言行为（R34/PF3）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RngtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 纯可执行包：无需 CMakeDeps（无可链接目标）
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 真实执行消费者测试二进制（内部驱动 rngtest/rngd 并断言行为）
        exe = os.path.join(self.cpp.build.bindir, "test_rng-tools")
        self.run(exe, env="conanrun")
