#!/usr/bin/env python3
"""Conan test_package — cmrc 2.0.1 消费者验证（L1 测试）。

真正调用被测物：find_package(cmrc) → cmrc_add_resource_library()
嵌入资源 → 编译并运行可执行程序读取资源内容并断言。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CmrcTestConan(ConanFile):
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
        # L0d: 显式 self.run() 直接执行两个消费者测试二进制（防空壳 stub）
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_cmrc", "test_ohos"):
            self.run(os.path.join(bindir, exe), env="conanrun")