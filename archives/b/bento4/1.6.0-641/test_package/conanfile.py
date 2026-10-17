#!/usr/bin/env python3
"""Conan test_package — bento4 1.6.0-641"""

import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Bento4TestConan(ConanFile):
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
        # 交叉编译场景下宿主无法执行目标架构二进制，跳过
        if can_run(self):
            # 只跑一次 test_bento4 二进制（cmake.test() 会重复执行同一目标，避免冗余）
            bin_path = os.path.join(self.build_folder, "test_bento4")
            self.run(bin_path, env="conanrun")
