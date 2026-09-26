#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — spline 1.2 (aspline) L1 消费者测试。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会**在 OHOS worker 上真实执行**，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 可写目录：测试要把输入数据集写成文件（aspline 读文件或 stdin），
  OHOS 上 /tmp 只读，因此在 self.build_folder 下建 scratch 目录并以 argv[2]
  传给测试程序；测试程序自己再探测一次可写性。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class SplineTestConan(ConanFile):
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
        bin_path = os.path.join(self.dependencies["spline"].package_folder,
                                "bin", "aspline")
        test_exe = os.path.join(self.cpp.build.bindir, "test_spline")
        scratch = os.path.join(self.build_folder, "spline_scratch")

        if cross_building(self):
            self.output.info(
                "cross-building: spline/aspline 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/aspline 未安装: {bin_path}")

        os.makedirs(scratch, exist_ok=True)
        self.run(f'"{test_exe}" "{bin_path}" "{scratch}"')
