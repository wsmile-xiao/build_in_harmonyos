#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for blisp.

CI runs this automatically via `conan create` (which invokes test_package).
The test links against libblisp and calls its public C API functions that
do not require hardware (crc32_calculate, chip descriptor queries).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BlispTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # 直接运行测试可执行文件（CI L0 门禁要求 test() 必须调用 self.run()）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            return
        self.run(os.path.join(bindirs[0], "test_blisp"), env="conanrun")
