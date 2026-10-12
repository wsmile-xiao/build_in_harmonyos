#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test (consumer view).

CI runs this automatically via `conan create` (which invokes test_package).
Builds test.cpp against the Conan package (headers + Boost.Test static library)
with CMake/CMakeDeps and executes the resulting Boost.Test executable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostTestConan(ConanFile):
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
        # 显式执行编译出的测试二进制（CI L0d 门禁要求显式 self.run 调用）
        self.run("./test_boost", cwd=self.build_folder, env="conanrun")
