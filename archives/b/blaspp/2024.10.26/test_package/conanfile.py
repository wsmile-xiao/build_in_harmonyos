#!/usr/bin/env python3
"""Conan test_package for blaspp 2024.10.26 — 消费者验证。

用上游公开 C++ API（<blas.hh>）编译并运行消费者程序：
  - find_package(blaspp CONFIG REQUIRED) 验证包配置可发现（lapackpp 下游同路径）
  - 断言 BLASPP_VERSION / blas::blaspp_version() == 20241026
  - 数值断言：axpy / dot / gemm / nrm2 对照手算参考值
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BlasppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # blaspp 的 BLAS/LAPACK 后端依赖：显式声明保证 CMakeDeps 在消费者
        # 图内生成 lapack::/cblas:: target（与 conanfile.package_info 的
        # cpp_info.requires 对应）
        self.requires("lapack/3.12.1")
        self.requires("cblas/3.12.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: explicit self.run() to satisfy CI gate
        bin_path = os.path.join(self.cpp.build.bindir, "test_blaspp")
        self.run(bin_path, env="conanrun")
