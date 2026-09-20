#!/usr/bin/env python3
"""Conan test_package for gamelib 1.9.9 — L1 消费者验证。

验证 header-only 库 gamelib 的 GameLib.SDL.h 头文件可被下游 C++ 程序
包含、链接 SDL2 并实际运行公开 API（消费方视角，R34）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GamelibTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # 消费者测试：真实调用 gamelib 公开 API 并断言可观察结果
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_gamelib"), env="conanrun")
        # 鸿蒙特有测试入口：平台宏 + gamelib API 实测
        self.run(os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test"), env="conanrun")
