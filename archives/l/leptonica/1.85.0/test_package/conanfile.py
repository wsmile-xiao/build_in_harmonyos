#!/usr/bin/env python3
"""Conan test_package — leptonica 1.85.0 (Conan L1 official test).

消费者功能测试：链接 leptonica 库并验证各依赖格式（PNG/JPEG/TIFF/GIF/JP2K）
的真实读写回环，测试程序对共享库的依赖由 conanrun env（LD_LIBRARY_PATH）解析。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LeptonicaTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0c/R34：test() 必须显式 self.run 执行测试二进制
        # （1.87.0 已合入配方同款双保险：ctest + 直接执行）。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_leptonica"), env="conanrun")
