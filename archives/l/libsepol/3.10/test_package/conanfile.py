#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsepolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
        # L0d: CI 静态规则要求 test() 中存在显式 self.run。
        # 直接前台运行 CMake 已构建的 test_sepol 二进制（不清除 CTest 验证）。
        self.run(os.path.join(self.build_folder, "test_sepol"), env="conanrun")