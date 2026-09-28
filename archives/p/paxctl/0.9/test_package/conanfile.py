#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — paxctl 0.9 L1 消费者测试。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会**在 OHOS worker 上真实执行**，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 可写目录：OHOS 上 /tmp 是只读文件系统，而 paxctl 必须对真实 ELF 文件做
  就地改写（-c / -m 等），因此测试需要一块可写空间。这里显式在
  self.build_folder 下建 scratch 子目录并传给测试程序（argv[2]），
  测试程序自己再探测一次可写性，绝不假定任何固定路径。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class PaxctlTestConan(ConanFile):
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
        bin_path = os.path.join(self.dependencies["paxctl"].package_folder,
                                "bin", "paxctl")
        test_exe = os.path.join(self.cpp.build.bindir, "test_paxctl")
        scratch = os.path.join(self.build_folder, "paxctl_scratch")

        if cross_building(self):
            self.output.info(
                "cross-building: paxctl 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/paxctl 未安装: {bin_path}")

        os.makedirs(scratch, exist_ok=True)
        self.run(f'"{test_exe}" "{bin_path}" "{scratch}"')
