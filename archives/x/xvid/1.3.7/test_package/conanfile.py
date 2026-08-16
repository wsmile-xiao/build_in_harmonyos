#!/usr/bin/env python3
"""Test package for xvidcore 1.3.7 — Conan L1 smoke test.

初始化 xvidcore 编码核心 (xvid_global/XVID_GBL_INIT)，验证头文件与库可用。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class XvidcoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")