#!/usr/bin/env python3
"""Conan test_package for fermi-lite 0.1 — L1 consumer test.

Compiles a C consumer against the packaged libfml.a and runs a real
assembly call (R34: must substantively use the tested package API).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FermiLiteTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d: run the consumer binary directly through self.run
        # (also satisfies the self.run() requirement of the L0 gate)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_fermi-lite")
        self.run(exe, env="conanrun")