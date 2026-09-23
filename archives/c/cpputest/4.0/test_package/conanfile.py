#!/usr/bin/env python3
"""test_package for cpputest — builds a real CppUTest suite and runs it.

Consumer verification: a C++ consumer writes test groups with real
assertions (LONGS_EQUAL/CHECK_TRUE/STRCMP_EQUAL/DOUBLES_EQUAL/
POINTERS_EQUAL/BYTES_EQUAL), drives them with CommandLineTestRunner and
asserts the runner exit code — no print-only empty shell (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CpputestTestConan(ConanFile):
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
        # Run the built consumer suite; exit code 0 = all assertions pass.
        # (CppUTest CommandLineTestRunner runs all tests by default; it has
        # no --run-all-tests flag — passing one prints usage and exits 1.)
        binp = os.path.join(self.cpp.build.bindirs[0], "cpputest_consumer_test")
        self.run(binp, env="conanrun")
