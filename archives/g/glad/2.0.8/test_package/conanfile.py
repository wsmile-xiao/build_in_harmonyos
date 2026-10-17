#!/usr/bin/env python3
"""Conan test_package — glad 2.0.8.

L1 官方测试：消费方程序 include <glad/gl.h> 并链接 libglad.a，
运行时用 stub proc-address 实际执行生成 loader 的表初始化逻辑；
另含 HarmonyOS 专项可执行用例（harmonyos_specific_test）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GladTestConan(ConanFile):
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
        # L0d: test() 必须实际执行测试可执行文件（self.run 真实运行）
        for test_bin in ("test_glad", "harmonyos_specific_test"):
            path = os.path.join(self.cpp.build.bindirs[0], test_bin)
            self.run(path, env="conanrun")
