#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/coinor-ipopt/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IpoptTestConan(ConanFile):
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
        # 直接用 conanrun 环境运行二进制：使配方 runenv_info 注入的
        # LD_LIBRARY_PATH（系统 libc++ 目录）生效，避免 ctest 缺运行库
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_coinor_ipopt")
        self.run(test_bin, env="conanrun")
