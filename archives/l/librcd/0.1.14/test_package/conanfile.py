#!/usr/bin/env python3
"""Test package for librcd 0.1.14 — Conan L1 official test.

用 Conan CMakeToolchain/CMakeDeps 编译 test_librcd.c 并链接被测包
（默认 cmake_file_name = 包名 → find_package(librcd) + librcd::librcd）。
测试源实质调用库唯一的公开 API `rcdGetRussianCharset()`（R34）：对 CP1251 /
KOI8-R / CP866 / UTF-8 四种编码的同一段俄文与 ISO-8859-1 拉丁文断言检测结果，
并覆盖 `len=0`（strlen 语义）与显式 `len=N` 两条入参路径。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrcdTestConan(ConanFile):
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
        # 再直接运行一次二进制（R34：消费方视角的实质 API 测试；
        # 输出 checks=<N> failures=0 作为机器可读证据行）
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_librcd"),
            env="conanrun",
        )
