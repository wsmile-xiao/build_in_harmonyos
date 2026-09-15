#!/usr/bin/env python3
"""Conan test_package — CLEX 4.6.patch8 消费者测试（运行包交付的工具并断言行为）。"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_clex")
        self.run(test_bin, env="conanrun")
