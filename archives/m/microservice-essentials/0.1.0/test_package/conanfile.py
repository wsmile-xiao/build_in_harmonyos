#!/usr/bin/env python3
"""Conan test_package — L1 官方测试 + 消费者验证。

test() 通过 self.run 实际执行消费者可执行文件（R34/PF3：禁止空壳/仅 cmake.test()）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MicroserviceessentialsTestConan(ConanFile):
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
        # 消费者验证：仅使用公开头文件/公开 API 模拟业务上层组件，真实编译链接运行
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_microservice_essentials"), env="conanrun")