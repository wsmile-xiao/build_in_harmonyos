#!/usr/bin/env python3
"""test_package — pastix/6.4.0 消费者视角验证（OHOS aarch64 真机运行）。

两个可执行文件：
  - test_pastix_solve：E2E 求解 2D 拉普拉斯稀疏系统（分析→分解→求解→收敛校验）
  - test_pastix_contract：6.4.0 宏/ABI 契约（版本/整型位宽/后端开关）

两者均以「逐检查 CHECK PASS/FAIL + TEST SUMMARY + 非零退出码」协议输出，
构建期即真实运行（真机 native）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PastixTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_pastix_solve"'.format(bindir), env="conanrun")
        self.run('"{}/test_pastix_contract"'.format(bindir), env="conanrun")
