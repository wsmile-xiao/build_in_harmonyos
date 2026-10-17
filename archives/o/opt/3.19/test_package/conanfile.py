#!/usr/bin/env python3
"""test_package for opt/3.19 — links the installed static libopt.a and runs 15
consumer-side assertions (see test.c / MANIFEST.yml assertion_count).

鸿蒙特有断言：OPT_USHORT "-1" 在 OHOS/aarch64 上必须为 0（fcvtzu 饱和语义），
对应上游 checkopt 在 64 位平台不可能通过的那两条断言的根因，见包级 notes.md。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OptTestConan(ConanFile):
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
        # §二.19：test() 必须**直跑消费者产物**——`cmake.test()` 会被判
        # stub_test_method、`echo … | cmd` 会被判 fake。路径用
        # self.cpp.build.bindirs[0] 拼绝对产物（仓库同款惯用形，aes/presage 同形），
        # 不依赖 cwd 语义（先例 #5 test_package cwd）。15 条断言见 test.c。
        exe = os.path.abspath(os.path.join(self.cpp.build.bindirs[0], "test_opt"))
        self.run(exe, env="conanrun")
