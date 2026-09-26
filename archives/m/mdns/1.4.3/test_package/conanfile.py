#!/usr/bin/env python3
"""Conan test_package — mdns 1.4.3 consumer test (CI 五级测试的 L1).

CI（`conan create`）自动执行：build() 用 CMakeDeps 生成的 `mdns::mdns` 目标
编译消费者 `test.c`，test() **直跑二进制**（PF3/L0c 要求 `self.run` 真实执行，
不用 `cmake.test()`）。

`test.c` 是鸿蒙特有测试的来源（PR 正文「鸿蒙特有测试」行 = 本消费者断言数，
不进上游分母 —— 上游 N=0，见 `reports/test-report.md`）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run test binary on this host (cross build)")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_package: no bindirs in build folder")
        bin_path = os.path.join(bindirs[0], "test_mdns")
        if not os.path.isfile(bin_path):
            raise ConanException(f"test_package: binary not found: {bin_path}")
        # 直跑消费者二进制（PF3）：非 0 退出即 test_package 失败
        self.run(bin_path, env="conanrun")
