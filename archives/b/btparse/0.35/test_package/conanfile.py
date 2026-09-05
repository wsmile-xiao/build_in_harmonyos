#!/usr/bin/env python3
"""Conan test_package — btparse 0.35 真实消费者验证.

构建一个真实消费者 test_btparse_api, 通过公共 API 完成:
  字符串条目解析 -> 字段遍历 -> 后处理取值 -> 姓名切分/格式化 -> 宏定义/删除。
全部断言失败时以非零退出码使 test_package 失败。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BtparseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_btparse_api"), env="conanrun")
