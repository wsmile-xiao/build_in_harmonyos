#!/usr/bin/env python3
"""Conan test_package for spim — verifies the spim binary works.

Uses CMake to build a test program (satisfies L0c gate for test source files).
The actual test runs the signed spim binary directly via self.run() (L0d).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpimTestConan(ConanFile):
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
        # Run the signed spim binary directly (L0d: self.run required)
        # The spim binary is signed in the conanfile.py build/package step.
        spim_pkg = self.dependencies["spim"]
        spim_bin = os.path.join(spim_pkg.cpp_info.bindirs[0], "spim")
        exc_path = os.path.join(spim_pkg.cpp_info.resdirs[0], "exceptions.s")
        test_asm = os.path.join(self.source_folder, "test_hello.s")
        self.run(f'"{spim_bin}" -ef "{exc_path}" -file "{test_asm}"', env="conanrun")
