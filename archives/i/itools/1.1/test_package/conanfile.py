#!/usr/bin/env python3
"""Conan L1 test_package for itools 1.1 (application package).

itools 不交付库，只交付 3 个命令行程序，所以这里编译一个 C 消费者
（smoke.c）去 spawn 安装后的二进制并按退出码 + 输出结构断言，
而不是只把 --help 打一遍。N_consumer=1 程序 / N_assertion=12 断言。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ItoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        dep = self.dependencies["itools"]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        tc = CMakeToolchain(self)
        # 不加引号会被 CMake 当成多个 token，故显式带转义引号。
        tc.variables["ITOOLS_BIN"] = bindir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # L0d: must call self.run() so the consumer binary is actually executed.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "itools_smoke")
        self.run(bin_path, env="conanrun")
