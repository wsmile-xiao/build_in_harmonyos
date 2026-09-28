#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — prctl 1.7 L1 消费者测试。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会**在 OHOS worker 上真实执行**，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class PrctlTestConan(ConanFile):
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
        bin_path = os.path.join(self.dependencies["prctl"].package_folder,
                                "bin", "prctl")
        test_exe = os.path.join(self.cpp.build.bindir, "test_prctl")

        if cross_building(self):
            self.output.info(
                "cross-building: prctl 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/prctl 未安装: {bin_path}")

        self.run(f'"{test_exe}" "{bin_path}"')
