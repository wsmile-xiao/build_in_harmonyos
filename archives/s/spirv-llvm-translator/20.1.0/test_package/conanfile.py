#!/usr/bin/env python3
"""Conan test_package — spirv-llvm-translator 20.1.0

L1 测试：编译链接验证 + 运行 llvm-spirv 二进制验证包完整性 (R34)。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpirvLlvmTranslatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("llvm/20.1.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # 执行被测包的二进制 (R34): 运行 llvm-spirv 验证可执行性
        # 使用显式路径，因为 VirtualRunEnv 可能不包含被测包的 bindirs
        dep = self.dependencies["spirv-llvm-translator"]
        bin_path = os.path.join(dep.package_folder, "bin", "llvm-spirv")
        self.run(f'"{bin_path}" --help', env="conanrun")
