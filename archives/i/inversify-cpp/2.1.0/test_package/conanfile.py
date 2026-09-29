#!/usr/bin/env python3
"""Conan test_package — inversify-cpp 2.1.0 消费者测试（header-only 交付形态）。

消费者面真实使用 inversify-cpp API：
- include <mosure/inversify.hpp>（来自 conan 包 include/ 交付件，非源码树）；
- 常量/动态绑定与重绑定、自动注入（构造参数注入）、unique/singleton 作用域、
  工厂绑定、嵌套注入链、未绑定符号的 ResolutionException、同型符号区分、
  绑定检视（INVERSIFY_BINDING_INSPECTION）与容器隔离；
- 23 条运行期 check 逐条打印读数 + 2 条编译期 static_assert（单列不混入运行期计数），
  任一失败退出码非 0。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class InversifyCppTestConan(ConanFile):
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
        # L0d 门禁：此处必须真实执行被测二进制（拒绝 echo/print/true 形态的空壳）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_inversify_cpp")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
