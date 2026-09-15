#!/usr/bin/env python3
"""Conan test_package — daa2iso 0.1.7e 消费者测试。

CMake 编译 test_daa2iso.c，test() 阶段把包内 bin/daa2iso 绝对路径作为 argv[1] 传入。
非 OHOS 目标（Windows 开发机）自动跳过运行时部分，CI 在 OHOS runner 上真实执行。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Daa2IsoTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("cross-building: daa2iso runtime checks deferred to OHOS runner")
            return
        bin_path = os.path.join(self.dependencies["daa2iso"].package_folder, "bin", "daa2iso")
        test_exe = os.path.join(self.cpp.build.bindir, "test_daa2iso")
        self.run(f'"{test_exe}" "{bin_path}"')
