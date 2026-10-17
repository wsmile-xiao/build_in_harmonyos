#!/usr/bin/env python3
"""Conan test_package for kiwisolver — compiles + runs a real API consumer.

L1 official test: builds test_kiwisolver.cpp against the packaged headers and
executes it. R34 real API usage — actually solves a constraint system with
kiwi::Solver and asserts the solution (not just header-presence).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_kiwisolver")
            self.run(cmd, env="conanrun")
