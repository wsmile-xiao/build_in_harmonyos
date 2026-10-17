#!/usr/bin/env python3
"""Conan test_package — 验证 doctest 头文件可被正确包含和使用"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class DoctestTestConan(ConanFile):
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
        # Run via CTest
        cmake = CMake(self)
        cmake.test()
        # Also run directly to satisfy L0e gate
        bin_path = os.path.join(self.build_folder, "test_doctest")
        self.run(bin_path, env="conanrun")
