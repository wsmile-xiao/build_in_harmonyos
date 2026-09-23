#!/usr/bin/env python3
"""Conan test_package for bcunit 5.3.113 — real API consumer.

Builds a C consumer against the packaged library (via CMakeDeps) and runs it;
the consumer exits non-zero if any of its checks fail: BCUnit counters must
report 3/3 tests with 0 failures, the 5.3.x suite user-data and partial JUnit
interfaces must behave as documented and the trace-handler hook must be
reachable through the framework's output path.

The consumer writes its JUnit output into the Conan build folder (cwd is set
explicitly), so no generated file lands in the package source directory.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BcunitTestConan(ConanFile):
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
        # Run the built consumer directly (product under test is the library;
        # the executable is the vehicle).  Absolute binary path + explicit cwd
        # keep every generated file inside the build folder.  Two invocations
        # because the upstream automated interface may only run once per
        # process (see test.c): full JUnit report, then partial JUnit report.
        binary = os.path.join(self.cpp.build.bindirs[0], "test_bcunit")
        self.run(binary, cwd=self.build_folder, env="conanrun")
        self.run(f"{binary} partial", cwd=self.build_folder, env="conanrun")
