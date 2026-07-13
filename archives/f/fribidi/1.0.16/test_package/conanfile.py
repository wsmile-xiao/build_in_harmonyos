#!/usr/bin/env python3
"""Conan test_package for fribidi 1.0.16 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is handled
by Conan toolchain, not raw shell env vars (R33).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class FribidiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_fribidi", env="conanrun")
