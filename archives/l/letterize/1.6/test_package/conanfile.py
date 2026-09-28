#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — letterize 1.6 L1 消费者测试。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  因此 cross_building(self) 为 False —— test() 会**在 OHOS worker 上真实执行**，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。
  本地 Windows x86 开发机 build profile 是 default，此时才跳过执行。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LetterizeTestConan(ConanFile):
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
        bin_path = os.path.join(self.dependencies["letterize"].package_folder,
                                "bin", "letterize")
        test_exe = os.path.join(self.cpp.build.bindir, "test_letterize")

        if cross_building(self):
            self.output.info(
                "cross-building: letterize 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/letterize 未安装: {bin_path}")

        self.run(f'"{test_exe}" "{bin_path}"')
