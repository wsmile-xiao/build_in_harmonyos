#!/usr/bin/env python3
"""Conan test_package — hsluv-c 1.0.0 消费者验证。

以第三方使用者身份通过安装后的公开头文件与链接目标使用 hsluv-c，
调用 hsluv2rgb / rgb2hsluv 并断言已知参考色（#ff0000）的转换结果，
验证可编译、可链接、可运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HsluvCTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_hsluv_consumer"), env="conanrun")