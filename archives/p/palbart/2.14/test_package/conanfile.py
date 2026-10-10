#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — palbart 2.14 消费者测试（CMake 构建 + 子进程行为断言）。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会在 OHOS worker 上真实执行，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 用例只跑「解释 + 编码」路径：既不调用 gnuplot/ghostscript 渲染，
  也不触碰网络或任何设备节点，产物只有 .lst 文本与 .bin 位流。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class PalbartTestConan(ConanFile):
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
                "cross-building: palbart 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not can_run(self):
            self.output.info("palbart runtime checks deferred to OHOS runner")
            return

        pkg = self.dependencies["palbart"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_palbart")
        self.run(f'"{exe}" "{pkg}"')
