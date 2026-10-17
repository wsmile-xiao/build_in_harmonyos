#!/usr/bin/env python3
"""Conan test_package — lwrb 3.3.0 消费者验证.

通过 Conan 生成的依赖配置（CMakeDeps/CMakeToolchain）构建消费者可执行文件，
并在 test() 中显式 self.run 实际运行（PF3 门禁：非空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LwrbTestConan(ConanFile):
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
        # 显式运行消费者可执行文件（真实编译链接运行，非仅检查存在）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lwrb")
        self.run(f"{bin_path}", env="conanrun")
