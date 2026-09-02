#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libayatana-common/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibayatanacommonTestConan(ConanFile):
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
        # 直接运行二进制并注入 conanrun 环境（LD_LIBRARY_PATH）：
        # 包内 .so 带 SONAME 后，运行时按 SONAME 查找，ctest 不注入
        # conanrun 环境会找不到 libayatana-common.so（与 libx11/glib 同法）。
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_libayatana-common")
        self.run(test_bin, env="conanrun")
