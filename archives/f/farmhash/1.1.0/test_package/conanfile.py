#!/usr/bin/env python3
"""Conan test_package for farmhash 1.1.0 — Conan L1 consumer test.

Verifies the installed libfarmhash API via 6 known-vector assertions
(test.cpp), CI runs this via `conan create` (invokes test_package).
File location: archives/f/farmhash/1.1.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FarmhashTestConan(ConanFile):
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
        # L0d: test() 必须通过 self.run() 实际运行消费者二进制（非 stub），
        # 运行 test_farmhash（test.cpp 内 6 个已知向量断言真实调用 libfarmhash API）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_farmhash"),
                 env="conanrun")
