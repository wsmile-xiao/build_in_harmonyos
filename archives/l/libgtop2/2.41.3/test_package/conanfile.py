#!/usr/bin/env python3
"""Conan test_package — libgtop2 2.41.3（L1 消费者测试）。

两个真实测试二进制（非空壳，R34）：
  test_libgtop2_api   —— 通用 API 断言（cpu/mem/uptime/sysinfo）
  test_libgtop2_ohos  —— 鸿蒙特有用例（/proc/stat 每 CPU、/proc 进程表、sysinfo ncpu）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgtop2TestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        for name in ("test_libgtop2_api", "test_libgtop2_ohos"):
            self.run(os.path.join(bindir, name), env="conanrun")
