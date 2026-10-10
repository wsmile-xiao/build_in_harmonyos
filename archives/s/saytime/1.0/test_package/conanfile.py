#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — saytime 1.0 消费者测试（CMake 构建 + 子进程行为断言）。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会在 OHOS worker 上真实执行，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 用例只跑「拼流」路径：saytime 不打开任何网络、不访问真实音频设备
  （/dev/audio 在 OHOS PC 上不存在，正好走 stdout 回退分支），
  产物只有 stdout 上的裸 PCM 字节流。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class SaytimeTestConan(ConanFile):
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
                "cross-building: saytime 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not can_run(self):
            self.output.info("saytime runtime checks deferred to OHOS runner")
            return

        pkg = self.dependencies["saytime"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_saytime")
        self.run(f'"{exe}" "{pkg}"')
