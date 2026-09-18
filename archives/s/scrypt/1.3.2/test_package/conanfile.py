#!/usr/bin/env python3
"""Conan test_package — scrypt 1.3.2 CLI 消费者验证（R02 修复版）。

R02 返工：test() 必须真实验证消费者路径，包含：
  1. 构建并运行编译出的 test_scrypt 可执行文件（test.c）
     —— test.c 内部逐步断言 scrypt --version / 加解密往返 / 错误口令必败，
        任何一步失败即退出码非 0（消除 R01 伪通过 P1/P2/P3）；
  2. 以已安装的 bin/scrypt 完整路径作为 argv[1] 传入 test_scrypt。
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ScryptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 编译 test.c -> test_scrypt 可执行文件（消费者测试载体）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        scrypt_bin = os.path.join(pkg_folder, "bin", "scrypt")
        self.output.info(f"testing scrypt binary: {scrypt_bin}")
        if not os.path.isfile(scrypt_bin):
            raise Exception(f"scrypt binary missing: {scrypt_bin}")
        test_exe = os.path.join(self.cpp.build.bindir, "test_scrypt")
        if not os.path.isfile(test_exe):
            raise Exception(f"test_scrypt not built: {test_exe}")
        # 实际运行编译出的消费者测试；argv[1] = 安装产物 scrypt 完整路径
        self.run(f'"{test_exe}" "{scrypt_bin}"', env="conanrun")
        self.output.info("scrypt consumer test PASSED")