#!/usr/bin/env python3
"""Conan test_package — chsrc L1 test.

R34: test_package 必须实质调用被测包的 API。
chsrc 是命令行工具，通过 C 测试程序编译并运行 chsrc --version 验证二进制可执行。
"""
import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ChsrcTestConan(ConanFile):
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
        # can_run() 守卫：交叉编译时跳过运行时测试（二进制为交叉架构，无法在宿主机执行）
        if not can_run(self):
            self.output.info("Skipping test: cross-building build platform cannot run target binaries")
            return
        # 运行编译出的 test_chsrc 二进制，传入 chsrc 完整路径作为参数
        # C 程序内部调用 system(chsrc_path --version) 验证二进制可执行
        test_bin = os.path.join(self.cpp.build.bindir, "test_chsrc")
        chsrc_bin = os.path.join(self.dependencies["chsrc"].package_folder, "usr", "bin", "chsrc")
        self.run(f"{test_bin} {chsrc_bin}", env="conanrun")
