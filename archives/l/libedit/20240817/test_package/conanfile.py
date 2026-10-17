#!/usr/bin/env python3
"""Conan test_package for libedit 20240817 — Library smoke test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run

class LibeditTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libedit")
            self.run(bin_path, env="conanrun")
        else:
            self.output.warning("Cannot run test binary (cross-compiling)")
