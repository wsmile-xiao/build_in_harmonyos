#!/usr/bin/env python3
"""Conan test_package — ctml 2.0.0 消费者视角真实用例（L1 / R34 / PF3）.

test() 用 self.run() 真实执行编译出的 test_ctml（PF3/CI L0c 口径），
test.cpp 里任一 CHECK 失败 → 进程 rc != 0 → conan create 失败。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CtmlTestConan(ConanFile):
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
        # PF3/L0c：必须真实执行被测二进制（断言失败 rc != 0 即让本测试失败）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ctml"), env="conanrun")
