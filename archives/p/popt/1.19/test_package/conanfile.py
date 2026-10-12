#!/usr/bin/env python3
"""Test package for popt — CMake-based."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PoptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 传入参数以真实验证 popt 解析路径（NONE/INT/STRING 三种类型 + 断言解析结果）
        self.run(os.path.join(self.build_folder, "test_popt")
                 + " -v -i 42 -o out.txt", env="conanrun")
