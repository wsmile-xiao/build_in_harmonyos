#!/usr/bin/env python3
"""Conan test_package — fungw 1.2.2 消费者测试（Conan L1 官方测试）。

test.c 是一个完整的消费者程序：初始化 fungw 上下文 -> 注册宿主对象与 C 函数
-> 分别用类型化调用 (fgw_vcall_in) 与字符串化调用 (fgw_scall) 触发被注册的
函数 -> 校验返回值与类型转换结果 -> 转储上下文 -> 释放。任一断言失败即非 0 退出。

CI 在 `conan create` 时自动执行本目录。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FungwTestConan(ConanFile):
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
        # 直接跑一次消费者程序，确认真的链接到被测包且全项断言通过
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fungw"), env="conanrun")
