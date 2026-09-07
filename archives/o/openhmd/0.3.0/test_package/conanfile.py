#!/usr/bin/env python3
"""Conan test_package for openhmd 0.3.0 — 上游 unittests 完整移植.

上游 tests/unittests/（autotools/meson 定义，CMake 构建不含）的 11 个
测试函数移植到消费者测试：vec3f×4 + quatf×5 + highlevel×2，另加公共
API 版本/枚举验证 ×2，共 13 个测试入口，断言与数据逐项对齐上游源码
（tests/unittests/{vec.c,quat.c,highlevel.c,main.c}）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenhmdTestConan(ConanFile):
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
        # ctest 跑 add_test(NAME test_openhmd ...)
        cmake = CMake(self)
        cmake.test()
        # 直接运行二进制，捕获上游风格的完整输出（"all a-ok" 尾行）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_openhmd")
        self.run(f'"{exe}"', env="conanrun")
