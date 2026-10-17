#!/usr/bin/env python3
"""Conan test_package for libnpy 1.0.1 — consumer verification (L1).

The consumer (test.cpp) exercises the INSTALLED header npy.hpp through the
full write/read roundtrip of the .npy format: 8 named checks covering
C/F-order roundtrips, magic bytes, dtype descr fingerprint, scalar and
empty-array shapes. test() runs the binary via self.run() (PF3/L0c/L0d).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibnpyTestConan(ConanFile):
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
        # PF3/L0c: test() 必须真实执行被测程序；cmake_layout 下 cwd=build 目录，
        # cpp.build.bindirs 为该目录下的绝对产物路径（§二.19：用绝对路径传参）
        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_libnpy"),
                env="conanrun",
            )
