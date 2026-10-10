#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — lpctools 1.07 消费者测试（CMake 构建 + 子进程行为断言）。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会在 OHOS worker 上真实执行，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 用例零硬件：串口路径全部指向 /dev/null，握手立刻 EOF，因此
  "连不上目标" 这条真实失败路径可以稳定复现，不需要接 LPC 板子。
  唯一触碰真实文件系统的是 lpc_binary_check 读一个空文件。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class LpctoolsTestConan(ConanFile):
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
            self.output.info(
                "cross-building: lpctools 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not can_run(self):
            self.output.info("lpctools runtime checks deferred to OHOS runner")
            return

        pkg = self.dependencies["lpctools"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_lpctools")
        self.run(f'"{exe}" "{pkg}"')
