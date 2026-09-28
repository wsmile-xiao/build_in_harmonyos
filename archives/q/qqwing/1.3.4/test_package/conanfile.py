#!/usr/bin/env python3
"""Conan test_package for qqwing 1.3.4 — consumer-side API verification."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QqwingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # OHOS 上 cmake 不在 PATH，显式指定 cmake 程序路径
        self.conf.define("tools.cmake:cmake_program", "/data/service/hnp/bin/cmake")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 含 self.run；直接运行消费者测试二进制（实质验证安装后的包）
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_qqwing')}", env="conanrun")
