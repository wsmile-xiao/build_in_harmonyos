#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test (consumer).

真实消费者用例：仅通过 lazycsv 已安装/导出的公开头文件 <lazycsv.hpp> 与
公开 API（lazycsv::parser / header() / cells() / raw() / trimmed() /
index_of()）编译、链接并运行，验证第三方使用者可正常使用该库。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LazycsvTestConan(ConanFile):
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
        # 直接运行消费者二进制（L0d: 必须含 self.run 调用，非 stub）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lazycsv"), env="conanrun")
