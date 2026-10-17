#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — unyaffs 0.9.7 L1 消费者测试。

★ OHOS CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64（host 与 build 相同），
  cross_building(self) 为 False —— test() 会**在 OHOS worker 上真实执行**，
  满足 CI L1a 门禁对 "test_package execution trace" 的要求。

★ 可写目录：提取类工具的测试必须写文件，OHOS 上 /tmp 只读，因此在
  self.build_folder 下建 scratch 目录并以 argv[2] 传给测试程序；
  测试程序自己再探测一次可写性，把「目录不可写」与「被测程序有缺陷」区分开。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class UnyaffsTestConan(ConanFile):
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
        bin_path = os.path.join(self.dependencies["unyaffs"].package_folder,
                                "bin", "unyaffs")
        test_exe = os.path.join(self.cpp.build.bindir, "test_unyaffs")
        scratch = os.path.join(self.build_folder, "unyaffs_scratch")

        if cross_building(self):
            self.output.info(
                "cross-building: unyaffs 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/unyaffs 未安装: {bin_path}")

        os.makedirs(scratch, exist_ok=True)
        self.run(f'"{test_exe}" "{bin_path}" "{scratch}"')
