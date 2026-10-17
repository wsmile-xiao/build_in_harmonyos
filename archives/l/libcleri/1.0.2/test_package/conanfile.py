#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libcleri/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibcleriTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libcleri 的公共头文件（inc/cleri/regex.h）直接 #include <pcre2.h>，
        # 消费者编译必须能看到 pcre2 的 include 目录。pcre2 通过 libcleri 的
        # cpp_info.requires 传递时，本上下文生成的 CMakeDeps 数据为空
        # （include/libs 缺失，见 E529 同类问题），因此 test_package 显式
        # 声明并链接 pcre2（与 archives/a/address-standardizer/3.7.0 的
        # 显式处理思路一致）。
        self.requires("pcre2/10.45.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libcleri')}", env="conanrun")
