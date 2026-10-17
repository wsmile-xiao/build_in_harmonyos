#!/usr/bin/env python3
"""Conan test package — easy_memory 0.7.0 (header-only C 库, CMake)

header-only 库: 编译并运行 test.c, 真实调用 em_create/em_alloc/em_free/em_destroy (R34)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EasymemoryTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_easy_memory")
        self.run(test_bin, env="conanrun")