#!/usr/bin/env python3
"""Conan test_package — osi L1 官方测试。

直接运行构建出的 test_osi 可执行文件（CMakeLists 未注册 CTest target，
避免 cmake.test() 依赖 enable_testing()）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OsiTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_osi")
        self.run(exe, env="conanrun")
