#!/usr/bin/env python3
"""Conan L1 test_package — libydpdict 消费者测试。

CI 通过 `conan create` 自动执行：先用 CMakeDeps 提供的 libydpdict::libydpdict
目标编译 test.c，再运行该二进制（test.c 内做真实 API 断言）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibydpdictTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: skip running test binaries")
            return
        bindir = self.cpp.build.bindirs[0]
        # 1) 单元/边界断言用例（test.c）
        self.run(os.path.join(bindir, "test_libydpdict"), env="conanrun")
        # 2) rule12 完整消费者用例（test_ydpdict_e2e.c）：真实生成词典文件对 →
        #    ydpdict_open → get_count/find_word/get_word（含 windows-1250→UTF-8 转换）→ close。
        #    必须在 test() 内真实执行，否则该用例只被编译、不构成"跑通"的消费者验证。
        self.run(os.path.join(bindir, "test_ydpdict_e2e"), env="conanrun")
