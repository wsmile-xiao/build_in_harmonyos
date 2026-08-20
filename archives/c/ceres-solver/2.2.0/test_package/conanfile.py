#!/usr/bin/env python3
"""Conan test_package for ceres-solver 2.2.0.

Tests that ceres-solver can be consumed and used to solve a simple
optimization problem with AutoDiff.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CeresSolverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require eigen so CMakeDeps generates Eigen3 config
        self.requires("eigen/3.4.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify ceres-solver API works
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_ceres_solver"),
            env="conanrun",
        )
