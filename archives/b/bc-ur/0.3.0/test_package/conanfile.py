#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/bc-ur/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BcurTestConan(ConanFile):
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
        # L0d: test() 必须通过 self.run() 实际执行测试二进制（真实运行，非空壳）。
        bindir = os.path.join(self.cpp.build.bindirs[0])
        self.run(os.path.join(bindir, "test_bc-ur"), env="conanrun")
        self.run(os.path.join(bindir, "test_bc-ur_ohos"), env="conanrun")
