#!/usr/bin/env python3
"""Conan test_package — soci 4.1.4 consumer test.

Builds a C++17 consumer against the installed soci (core + SQLite3 backend) and
runs it.  The consumer drives the public API over an in-memory SQLite database:
DDL, parameterised inserts via use(), reads via into(), rowset iteration, a
prepared statement re-executed with new bound values, plus two negative cases
checking that bad SQL and a missing column raise soci_error (see
src/test_soci.cpp).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SociTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_soci")
        self.run(test_bin, env="conanrun")
