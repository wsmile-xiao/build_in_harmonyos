#!/usr/bin/env python3
"""Conan test_package — msdfgen 1.13 消费者验证.

从最终 Conan 包构建消费者程序（CMakeDeps: msdfgen::msdfgen），
运行后断言全部通过才算成功。同时把仓库既有 conandata 声明的
源码 URL/SHA256 留在 notes 里供审计。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class MsdfgenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        VirtualRunEnv(self).generate()
        binary = os.path.join(self.cpp.build.bindirs[0], "test_msdfgen")
        self.run(f'"{binary}"', env="conanrun")
