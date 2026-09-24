#!/usr/bin/env python3
"""Conan test_package — pbc-sig 0.0.8 L1 test.

Substantive test: initializes a Type A pairing, generates BLS
system parameters, signs and verifies "hello world".
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PbcSigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("pbc/1.0.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly to satisfy R34/PF3 stub_test_method gate
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_pbc_sig"), env="conanrun")
