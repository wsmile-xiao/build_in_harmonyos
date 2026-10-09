#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — pm-utils 1.4.1 消费者测试（CMake 构建 + 子进程行为断言）。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会在 OHOS worker 上真实执行，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 用例零特权、零硬件：pm-pmu 的目标路径 /sys/devices/system/cpu/intel_pstate/
  在 OHOS 上不存在，所以走的正是「优雅降级」分支；pm-reset-swap 的参数只用
  /dev/null、/dev/zero 和一个不存在的路径，都不需要特权。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class PmUtilsTestConan(ConanFile):
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
                "cross-building: pm-utils 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not can_run(self):
            self.output.info("pm-utils runtime checks deferred to OHOS runner")
            return

        pkg = self.dependencies["pm-utils"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_pm_utils")
        self.run(f'"{exe}" "{pkg}"')
