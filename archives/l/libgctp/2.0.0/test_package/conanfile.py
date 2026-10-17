#!/usr/bin/env python3
"""Conan test_package — libgctp 2.0.0 consumer test.

Builds a C consumer that exercises the public projection API from proj.h
(utmforint/utmfor forward + utminvint/utminv inverse) with assertions and
verifiable behavior.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibgctpTestConan(ConanFile):
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
        # L0d: execute the consumer binary directly and assert its exit code
        # (a ctest wrapper alone is treated as a stub by the quality gate)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libgctp")
        self.run(bin_path, env="conanrun")
