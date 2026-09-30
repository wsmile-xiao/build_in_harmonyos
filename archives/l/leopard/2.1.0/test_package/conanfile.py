#!/usr/bin/env python3
"""Conan consumer test for the leopard 2.1.0 header-only package."""

import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LeopardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer executable was not run")
            return
        # 真实执行消费者可执行文件；其退出码就是 test_leopard.cpp 里 10 项
        # 断言的判定结果（输出 CHECKS=10 FAILURES=0）。按 L0d 要求 test()
        # 必须走 self.run 真实执行，而不是只靠 ctest 目标。
        candidates = sorted(glob.glob(os.path.join(self.build_folder, "**", "test_leopard"),
                                      recursive=True))
        if not candidates:
            raise RuntimeError("test_leopard consumer executable not found under %s"
                               % self.build_folder)
        self.run(candidates[0], env="conanrun")
