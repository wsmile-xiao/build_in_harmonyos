#!/usr/bin/env python3
"""Conan test_package for scip 10.0.3 — Conan L1 consumer test.

Creates a SCIP environment, builds a simple MIP problem, solves it,
and verifies the solution. This tests that the library links correctly
and the LP solver (SoPlex) is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class ScipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_scip")
            self.run(f"{bash} -c '{bin_path}'", env="conarrun")
