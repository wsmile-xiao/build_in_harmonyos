#!/usr/bin/env python3
"""test_package — HandmadeMath 2.0.0 消费者测试。

include HandmadeMath.h 并实际调用向量/矩阵 API（HMM_V4/HMM_NormV4/HMM_LenV4/
HMM_DotV4/HMM_M4D/HMM_MulM4）验证头文件库可被消费者编译链接使用（R34）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HandmadeMathTestConan(ConanFile):
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
        # L0d: test() 必须包含 self.run() 并真实运行由 CMake 构建的消费者测试程序
        #（R33: 不依赖未定义 shell 变量；路径来自 build 目录，非裸 ${VAR}）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_handmade-math"), env="conanrun")
