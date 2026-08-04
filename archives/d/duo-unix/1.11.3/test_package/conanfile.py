#!/usr/bin/env python3
"""Conan test_package for duo-unix — verifies libduo API linkage.

L1 official test: compiles a consumer program that links against libduo and
exercises the duo_open/duo_close API. The L1e destructive negative test
confirms the test genuinely depends on the package (removing libduo breaks
compilation/linking).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DuoUnixTestConan(ConanFile):
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
        cmake = CMake(self)
        # 运行 CMake 构建出的 test_duo 可执行文件
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_duo")
        self.run(cmd, env="conanrun")
