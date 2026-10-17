#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/audaspace/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudaspaceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # E298: 显式运行并启用 conanrun 环境，避免共享库找不到
        test_bin = os.path.join(self.cpp.build.bindir, "test_audaspace")
        if os.path.exists(test_bin):
            self.run(f'"{test_bin}"', env="conanrun")
        else:
            # fallback to CTest with output
            cmake = CMake(self)
            cmake.test()
