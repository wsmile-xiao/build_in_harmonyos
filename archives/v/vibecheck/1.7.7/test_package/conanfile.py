#!/usr/bin/env python3
"""Conan test_package — vibecheck 1.7.7 (Go CLI) L1 official test.

This is the L1 test in the five-level test system.  CI runs this automatically
via `conan create` (which invokes test_package).

vibecheck is a pure-Go CLI.  The main conanfile.py bootstraps a Go >= 1.24
toolchain and runs the upstream 115 `go test` Test* functions on the device.
This test package additionally runs a standalone C program (test.c) that
reimplements and asserts the same cases for a few core pure-logic mappings of
the upstream Go Test* functions.  The test program runs on HarmonyOS PC via
CMake + clang and emits the HMBS_TEST_PACKAGE_RESULT marker with its real
counts.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VibecheckTestConan(ConanFile):
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
        # Run the standalone C verification binary directly.  The program
        # emits the HMBS_TEST_PACKAGE_RESULT marker and exits 0 on success.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_vibecheck"),
            env="conanrun",
        )
