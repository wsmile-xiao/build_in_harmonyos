#!/usr/bin/env python3
"""Conan test_package — qdldl 0.1.8 L1 消费者测试。

由 conan create 自动执行：构建 test_qdldl（真实调用 QDLDL API），
再经 test() 运行二进制验证链接与功能。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QdldlTestConan(ConanFile):
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
        # 实际运行消费者测试二进制（test.c 真实调用 qdldl 的 LDL^T API）
        self.run("./test_qdldl", env="conanrun")
