#!/usr/bin/env python3
"""Consumer test for divsufsort 2.0.1.

Links against the divsufsort / divsufsort64 components, constructs a
suffix array and BWT on a known input string, and verifies the results
are correct.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DivSufSortTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer linked but cannot run")
            return
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_divsufsort"),
            env="conanrun",
        )
