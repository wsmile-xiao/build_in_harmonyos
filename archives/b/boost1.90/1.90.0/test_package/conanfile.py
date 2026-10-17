#!/usr/bin/env python3
"""Conan test_package — boost1.90 1.90.0 L1 smoke test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostTestConan(ConanFile):
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
        cmake.test()
        # L0d 门禁要求 test() 中存在显式 self.run() 调用，
        # 直接运行构建产物 test_boost 满足该判定（cmake.test() 之外显式执行一次）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_boost"))
