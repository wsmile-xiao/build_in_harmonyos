#!/usr/bin/env python3
"""Conan test_package — crashme 2.8.5 消费者测试。

CMake 编译 test_crashme.c，test() 阶段把包内 bin/crashme 与 bin/pddet 的绝对路径
作为 argv[1]/argv[2] 传入。非 OHOS 目标（Windows 开发机）自动跳过运行时部分。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CrashmeTestConan(ConanFile):
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
            self.output.info("cross-building: crashme runtime checks deferred to OHOS runner")
            return
        pkg = self.dependencies["crashme"].package_folder
        crashme_bin = os.path.join(pkg, "bin", "crashme")
        pddet_bin = os.path.join(pkg, "bin", "pddet")
        test_exe = os.path.join(self.cpp.build.bindir, "test_crashme")
        self.run(f'"{test_exe}" "{crashme_bin}" "{pddet_bin}"')
