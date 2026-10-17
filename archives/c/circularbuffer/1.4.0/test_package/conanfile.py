#!/usr/bin/env python3
"""Conan test_package — circularbuffer 1.4.0 (L1 official test).

消费者视角验证：仅通过已安装的公开头文件 <CircularBuffer.hpp>
使用 CircularBuffer<T,S> 模板的公开 API（push/shift/pop/unshift/
first/last/size/available/isEmpty/isFull/clear），编译、链接并运行。
R34：test() 必须真实调用被测库 API，禁止空壳。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CircularbufferTestConan(ConanFile):
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
        # L0d 门禁要求 test() 内含 self.run()（真实执行被测二进制）。
        # 直接运行 test_circularbuffer 可执行文件，校验退出码 0。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_circularbuffer"),
                 env="conanrun")
