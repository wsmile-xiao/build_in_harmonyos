#!/usr/bin/env python3
"""Conan test_package — extra-cmake-modules L1 test.

R34: test_package 必须实质调用被测包的 API/CMake 模块。
ECM 是 cmake-only 模块包，"调用 ECM API" = find_package(ECM) 并使用其提供的 cmake 宏。
本测试用 ECMAddAppIcon 验证 ECM 模块可被 find_package 正确导入。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ExtraCMakeModulesTestConan(ConanFile):
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
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序，cmake.test() 不被门禁识别
        test_bin = os.path.join(self.build_folder, "test_ecm")
        self.run(test_bin, env="conanrun")
