#!/usr/bin/env python3
"""Conan test_package — ColPack 1.0.10 消费者测试（真实调用库 API）。"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ColpackTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_colpack")
        self.run(test_bin, env="conanrun")
