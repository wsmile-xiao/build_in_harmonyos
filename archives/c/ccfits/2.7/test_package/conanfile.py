#!/usr/bin/env python3
"""Conan test_package for CCfits 2.7.

Consumer-side functional smoke test. Builds test_ccfits.cpp, which exercises
the real public CCfits API (FITS construction with image geometry, keyword
cards, image pixel writes/reads, binary table string column round-trip) and
asserts a write -> reopen -> read round-trip. Run via `conan create` (which
invokes test_package automatically).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CcfitsTestConan(ConanFile):
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
        # Run the test executable directly via self.run() so the L0d gate
        # detects an actual test invocation (cmake.test() is not recognized).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_ccfits")
        self.run(exe, env=["LD_LIBRARY_PATH"])
