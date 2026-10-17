#!/usr/bin/env python3
"""cpp-rotor 0.35 test_package — 消费者实质测试。

在 conan create 阶段以真实 cpp-rotor API 构建并运行 test_cpp-rotor 二进制，
证明库可链接、可运行（非空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import can_run


class CpprotorTestConan(ConanFile):
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
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], "test_cpp-rotor")
            self.run(exe, env="conanrun")
