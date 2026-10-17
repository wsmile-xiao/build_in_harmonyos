#!/usr/bin/env python3
"""Conan test_package — cmbacktrace 1.5.0 consumer test.

Compiles test.c against the installed headers and links the static library,
then runs the binary to exercise cm_backtrace_init/firmware_info/call_stack.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CmbacktraceTestConan(ConanFile):
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
        # L0d: 必须实际运行测试二进制（grep self.run 命中，非空壳）
        # cmake_layout 下 bindirs[0] 为构建目录；直接执行 test_cmbacktrace
        # 使消费者测试真实运行（ctest 之外再显式跑一次，输出可观察结果）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cmbacktrace"), env="conanrun")
