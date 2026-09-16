#!/usr/bin/env python3
"""Conan test_package — plutobook 0.19.0 消费者视角测试（L1）

真实调用 plutobook C API 渲染 PDF 并校验产物（R34，禁止空壳测试）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PlutobookTestConan(ConanFile):
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
        # L0d/R34：显式 self.run 执行消费者测试二进制（test.c 真实调用 plutobook C API）。
        # can_run：交叉构建（如 WSL 编 aarch64 交付物）时跳过执行，设备/CI 原生构建时真实执行。
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_plutobook"), env="conanrun")
