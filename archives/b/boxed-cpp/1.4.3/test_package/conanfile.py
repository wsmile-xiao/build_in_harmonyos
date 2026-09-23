#!/usr/bin/env python3
"""Conan test_package for boxed-cpp 1.4.3 — consumer test.

Compiles a C++20 program that includes boxed-cpp/boxed.hpp and exercises the
public API (boxed construction, unbox(), .as<T>(), boxed_cast, arithmetic)
with runtime assertions, then runs it on the target. This validates that the
installed header is usable from a downstream project.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoxedCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-build: skipping consumer run on host")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
