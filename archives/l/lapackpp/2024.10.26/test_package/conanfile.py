#!/usr/bin/env python3
"""Conan test_package for lapackpp 2024.10.26 — 消费者验证。

用上游公开 C++ API（<lapack.hh>）编译并运行消费者程序：
  - find_package(lapackpp CONFIG REQUIRED) 验证包配置可发现（SLATE 下游同路径）
  - 断言 LAPACKPP_VERSION / lapack::lapackpp_version() == 20241026
  - 数值断言：potrf / gesv / getrf+getrs / trtri / geqrf+orgqr / syev / gesvd
    对照手算参考值或可验证不变量（L·Lᵀ==A、QᵀQ==I、U·U⁻¹==I、残差≈0）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LapackppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lapackpp 的 BLAS++/LAPACK/CBLAS 后端：显式声明保证 CMakeDeps 在消费者
        # 图内生成 blaspp::/lapack::/cblas:: target（与 conanfile.package_info 的
        # cpp_info.requires 对应）
        self.requires("blaspp/2024.10.26")
        self.requires("lapack/3.12.1")
        self.requires("cblas/3.12.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: 真实执行本包产出的消费者二进制并断言其输出（非占位式测试）
        bin_path = os.path.join(self.cpp.build.bindir, "test_lapackpp")
        self.run(bin_path, env="conanrun")
