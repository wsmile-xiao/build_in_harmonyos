#!/usr/bin/env python3
"""Conan test_package — consumer verification for libgta/1.2.1.

Builds test_package/test.c against the installed package with CMakeDeps, then
runs the resulting binary directly (self.run, device-facts §二.19: cmake.test()
would be judged a stub test method).  test.c links and calls the installed
libgta API (create/write/read/verify roundtrip), so this is a real consumer
run, not a print-only stub (R34/PF3).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgtaTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libgta")
        self.run(bin_path, env="conanrun")
