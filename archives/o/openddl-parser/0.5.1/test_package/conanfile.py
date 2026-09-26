#!/usr/bin/env python3
"""Conan test_package — openddl-parser 0.5.1（L1 消费者测试）。

PF3/L0d: test() 必须 self.run() 真实执行被测包链接出的二进制，
不允许 cmake.test() 空转（L0c/L1d 实测会判 stub/fake）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenddlparserTestConan(ConanFile):
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
        # 真实执行消费者测试二进制（9 条断言：版本接口 / 合法解析 / 树结构 / 垃圾输入拒绝）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_openddlparser"),
                 env="conanrun")
