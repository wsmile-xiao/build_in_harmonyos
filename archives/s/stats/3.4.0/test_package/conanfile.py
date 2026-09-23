#!/usr/bin/env python3
"""Conan L1 test_package — stats 3.4.0 (header-only statistics library).

Compiles a consumer program that calls the real StatsLib API
(dnorm/pnorm/qnorm plus a seeded rnorm draw) and asserts numeric results,
so the test verifies headers + the GCEM transitive include chain end-to-end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class StatsTestConan(ConanFile):
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
        # Run the consumer binary directly (real API execution, PF3/L0d).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_stats")
        self.run('"%s"' % bin_path, env="conanrun")
