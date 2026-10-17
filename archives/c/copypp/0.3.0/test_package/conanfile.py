#!/usr/bin/env python3
"""Conan test_package — copypp 0.3.0 消费者测试（鸿蒙特有测试行）。

只通过打包后的 include 与导入目标 icurve::copypp 使用上游 API，
断言为显式计数（不依赖 assert/NDEBUG），任一失败进程非零退出（R34 反空壳）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CopyppTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 上游库与测试面要求 C++20（头文件 #error），对齐 conan toolchain 默认 17
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "20"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_copypp")
            self.run(executable, env="conanrun")
        else:
            self.output.info(
                "Cross-building: test_package execution is covered by the device test"
            )
