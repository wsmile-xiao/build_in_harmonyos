#!/usr/bin/env python3
"""Conan test_package for libgmpxx 6.3.0 — verifies GMP C++ bindings work."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgmpxxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gmpxx.h 公开头展开需要 gmp.h：显式直接依赖，保证 CMakeDeps
        # 为 gmp 生成完整 include 数据（传递依赖会被 Conan 2 置空）
        self.requires("gmp/6.3.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d: explicit self.run() to satisfy CI gate
        bin_path = os.path.join(self.cpp.build.bindir, "test_gmpxx")
        self.run(bin_path, env="conanrun")
