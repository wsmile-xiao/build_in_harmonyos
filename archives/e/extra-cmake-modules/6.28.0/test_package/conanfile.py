#!/usr/bin/env python3
"""Conan test_package — extra-cmake-modules L1 test.

R34: test_package 必须实质调用被测包的 API/CMake 模块。
ECM 是 cmake-only 模块包，"调用 ECM API" = find_package(ECM) 并使用其 cmake 宏。
build() 通过 CMake 验证 find_package(ECM) + 模块加载，test() 执行验证脚本。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ExtraCMakeModulesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 强制跳过编译器检查（ECM 是纯 cmake 模块包，不编译任何代码）
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        # 验证 find_package(ECM) 和关键 ECM 模块可被 CMake 加载
        cmake = CMake(self)
        cmake.configure()

    def test(self):
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序
        test_script = os.path.join(self.source_folder, "src", "test_ecm.sh")
        self.run(f"/bin/sh {test_script}", env="conanrun")
