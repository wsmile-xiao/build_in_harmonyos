#!/usr/bin/env python3
"""Conan consumer test for GoogleTest 1.18.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GoogletestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError("consumer test bindirs are unavailable")
            executable = os.path.join(bindirs[0], "test_googletest")
            if not os.path.isfile(executable):
                raise RuntimeError(f"consumer test binary is missing: {executable}")
            self.run(executable, env="conanrun")
