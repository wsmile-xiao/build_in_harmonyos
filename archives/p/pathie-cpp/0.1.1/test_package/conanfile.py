#!/usr/bin/env python3
"""Conan test_package — pathie-cpp 0.1.1（L2 消费者测试）。

PF3/L0d: test() 必须 self.run() 真实执行链接了被测包的二进制，
不允许 echo/print/true 空转，也不允许只跑 ctest 而无断言。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PathieCppTestConan(ConanFile):
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
        # 真实执行消费者测试二进制（14 条断言：版本接口 / 路径归一 / 目录与扩展名 /
        # join·prune / native 回转 / iconv 转码 / 流替换读写 / 建删目录）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_pathie_cpp"),
                 env="conanrun")
