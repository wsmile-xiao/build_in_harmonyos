#!/usr/bin/env python3
"""Conan test_package — numcpp 2.16.1 consumer test.

Builds a real executable that includes the full NumCpp.hpp umbrella (this
parses every NumCpp module header under default Boost-enabled settings) and
verifies representative numeric behaviour end to end:
  * NdArray construction/arithmetic/reductions, arange/reshape/transpose
  * matrix multiplication (nc::dot)
  * Boost.Math-backed special functions (nc::special::gamma)
  * Boost.DateTime-backed DateTime string round-trip
  * Boost.Polynomial-backed nc::polynomial::chebyshev_t
  * random normal statistical sanity + gcd/lcm
The program counts every check and exits non-zero on any failure; conan
create therefore fails if the packaged headers (or the propagated Boost
headers) are broken.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NumCppTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_numcpp"),
                 env="conanrun")
