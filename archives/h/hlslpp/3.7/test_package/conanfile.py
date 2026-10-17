#!/usr/bin/env python3
"""test_package — hlslpp 3.7 消费者端到端测试（L1 / rule12）.

真实以消费者身份 find_package(hlslpp) 并 include <hlsl++.h>，完整走一遍
图形/游戏应用最典型的 HLSL 风格数学流程：视图/投影矩阵构造 → MVP 拼接 →
顶点变换 → 四元数旋转 → 逆变换回环验证，而非纯断言或空壳调用。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HlslppTestConan(ConanFile):
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
        # L0d: test() 必须包含 self.run() 并真实运行构建出的消费者程序
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_hlslpp"),
                 env="conanrun")
