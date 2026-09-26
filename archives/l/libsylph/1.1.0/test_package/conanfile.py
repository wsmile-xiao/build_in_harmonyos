#!/usr/bin/env python3
"""Conan test_package — libsylph 1.1.0 消费者测试（赛道二硬门禁：真实编译+链接+调用 API+断言）。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibsylphTestConan(ConanFile):
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
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_libsylph"),
                     env="conanrun")
