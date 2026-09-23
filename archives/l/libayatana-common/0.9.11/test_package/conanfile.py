#!/usr/bin/env python3
"""Conan test_package for libayatana-common — L1 official test (CMake+test.c).

借鉴 0.9.13：test_package 用 CMake 真实编译 test.c（调 is_lomiri 等 API），
而非纯文件存在校验——R34 真实产物 + API 调用验证。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibayatanaCommonTestConan(ConanFile):
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
        # conanrun 环境会找不到 libayatana-common.so（与 0.9.13 同法）。
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_libayatana-common")
        self.run(test_bin, env="conanrun")
