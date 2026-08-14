#!/usr/bin/env python3
"""Conan test_package for clp 1.17.10 — links and runs ClpSimplex (R34)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClpTestConan(ConanFile):
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
        # L0d 门禁要求 test_package/conanfile.py 含 self.run 调用：
        # 直接运行构建出的 test_clp 二进制（真实链接验证，R34）。
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_clp")
        self.run(test_bin, env="conanrun")
