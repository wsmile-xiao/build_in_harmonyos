#!/usr/bin/env python3
"""Conan test_package — exprtk 消费者测试（真实调用库 API 并断言行为）+ 鸿蒙专项测试."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ExprtkTestConan(ConanFile):
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
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_exprtk"), env="conanrun"
        )
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test"),
            env="conanrun",
        )
