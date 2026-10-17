#!/usr/bin/env python3
"""Conan test_package — flatbush 1.5.0.

L1 测试：真实调用 flatbush 公开 API（FlatbushBuilder.add/finish/search），
验证第三方使用者可编译、链接并正确运行（R34）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FlatbushTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_flatbush"), env="conanrun")
