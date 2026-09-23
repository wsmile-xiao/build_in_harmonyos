#!/usr/bin/env python3
"""Conan test_package — mlddc 1.0 L1 test.

L1 test: 编译并运行 test.c——fork+exec 运行包内 mlddc 二进制（绝对路径），
验证程序可执行且无输入时退出码为预期值 10（Invalid user data）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MlddcTestConan(ConanFile):
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
        # 用依赖包绝对路径运行 mlddc（conanrun 环境不保证 bin 在 PATH）
        mlddc_bin = os.path.join(
            self.dependencies["mlddc"].package_folder, "bin", "mlddc")
        self.run(f"test -x {mlddc_bin}")
        test_exe = os.path.join(self.cpp.build.bindir, "test_mlddc")
        self.run(f"{test_exe} {mlddc_bin}")
