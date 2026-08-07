#!/usr/bin/env python3
"""Conan test_package — wavpack 5.9.0 L1 smoke test.

Uses CMake (CMakeDeps + CMakeToolchain) to consume the wavpack package
and verify the library API via an encode → decode roundtrip test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class WavpackTestConan(ConanFile):
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
        # 运行测试二进制 — 成功返回 0 (L0d: 必须显式 self.run)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_wavpack"), env="conanrun")
