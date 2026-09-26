#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan test_package — lunar 2.2 L1 消费者测试。

- build(): 用 CMake 交叉编译 test_lunar.c（目标 aarch64-linux-ohos）
- test():  传入包内已安装的 bin/lunar 与 share/lunar，执行消费者测试

★ OHOS CI 的关键事实：CI 用 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  （host 与 build profile 相同），因此 conan 的 cross_building(self) 判定为
  False —— test() 会**在 OHOS worker 上真实执行**，不是被跳过。这正是 CI
  L1 门禁（L1a）要求的 "test_package execution trace"。
  本地 Windows x86 开发机上 build profile 是 default，cross_building 为
  True，此时才跳过执行并打印提示。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LunarTestConan(ConanFile):
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
        pkg = self.dependencies["lunar"].package_folder
        bin_path = os.path.join(pkg, "bin", "lunar")
        data_dir = os.path.join(pkg, "share", "lunar")
        test_exe = os.path.join(self.cpp.build.bindir, "test_lunar")

        if cross_building(self):
            # 本地（Windows x86）无法执行 aarch64 ELF；CI 端 host==build，
            # 该分支不会走到，test() 会被真实执行。
            self.output.info(
                "cross-building: lunar 消费者测试在 OHOS 目标上执行（CI host==build）")
            return

        if not os.path.isfile(bin_path):
            raise ConanException(f"bin/lunar 未安装: {bin_path}")

        self.run(f'"{test_exe}" "{bin_path}" "{data_dir}"')
