#!/usr/bin/env python3
"""Conan test_package — access_profiler L1 消费者验证。

test_package 以消费者视角（仅用安装产物中的公开头文件 access_profiler.hpp
与公开 API access_profiler::instrument_type<T>，链接 libaccess_profiler.a）
验证包可编译、链接、运行：实例化 instrument_type 类型并执行字段读写，
断言可观察结果（聚合值）正确。test() 通过 self.run 实际执行测试二进制
（L0d 门禁要求，且为真实运行而非空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AccessProfilerTestConan(ConanFile):
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
        # 实际运行消费者测试二进制（公开 API 字段聚合断言）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_access_profiler"),
                 env="conanrun")
