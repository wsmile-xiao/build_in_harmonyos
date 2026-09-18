#!/usr/bin/env python3
"""Conan test_package — kernel-headers 6.12.77 L1 冒烟测试（消费者视角 R34）."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KernelHeadersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d/R34 门禁：test() 显式 self.run() 执行构建产物
        # （编译期 #error 断言 + 运行期版本/宏/结构体联合校验，
        #  退出码 0 判定通过）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_kernel_headers"), env="conanrun")
