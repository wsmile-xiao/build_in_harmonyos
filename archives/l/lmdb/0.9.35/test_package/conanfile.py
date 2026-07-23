#!/usr/bin/env python3
"""Conan test_package for lmdb 0.9.35 — validates put/get via LMDB API."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LmdbTestConan(ConanFile):
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
        # Run the test binary directly (L0d requires self.run() in test)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_lmdb")
        self.run(exe, env="conanrun")