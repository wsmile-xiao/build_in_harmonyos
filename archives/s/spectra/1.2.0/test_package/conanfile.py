#!/usr/bin/env python3
"""Conan test_package — spectra 1.2.0 (header-only C++ library).

L1 test: compile a small C++ program that includes spectra and Eigen headers,
computes eigenvalues of a symmetric matrix, and cross-validates with Eigen.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpectraTestConan(ConanFile):
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
        # 运行测试二进制 — 成功返回 0
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_spectra"), env="conanrun")
