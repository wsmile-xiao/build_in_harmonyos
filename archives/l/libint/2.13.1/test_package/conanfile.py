#!/usr/bin/env python3
"""Conan test_package — libint 2.13.1 消费者验证。

R34：测试必须实质调用被测包 API。本测试用 libint2 C++ API
构造两个归一化 1s Shell 并计算重叠积分，断言 S_ss ≈ 1.0
（两个相同 s 型高斯基函数同中心时重叠积分为 1）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # C++ API 头文件需要 Eigen3（transitive_headers 之外显式声明，保证可编译）
        self.requires("eigen/3.4.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34/L0d: test() 必须实质运行被测包二进制（禁止空壳 print-only）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libint"),
                 env="conanrun")
