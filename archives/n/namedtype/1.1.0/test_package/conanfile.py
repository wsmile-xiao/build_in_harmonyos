#!/usr/bin/env python3
"""Conan test_package for namedtype 1.1.0 — Conan L1 官方消费者测试.

CI（ci/conan/build_and_test.sh）在 `conan create` 之后自动构建并运行本目录：
  L0a-L0e 目录/conanfile/源码/test()/MANIFEST 五项门禁
  L1a-L1e 真实编译链接 + 真实执行（自检为假测试会拦）
File location: archives/n/namedtype/1.1.0/test_package/conanfile.py
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class NamedtypeTestConan(ConanFile):
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
        # PF3/L0c：真实执行消费者二进制——断言失败会以非零码退出，
        # 坏包不可能静默通过。
        if not can_run(self):
            raise Exception("can_run=False：本包的消费者测试必须在目标机执行")
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_namedtype")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
