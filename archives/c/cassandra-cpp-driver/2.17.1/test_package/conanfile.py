#!/usr/bin/env python3
"""Conan test_package for cassandra-cpp-driver 2.17.1.

L1 test: verifies the library can be linked and its API is functional.
Creates a CassCluster and CassSession, then frees them.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CassandraCppDriverTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_cassandra_cpp_driver")
        self.run(test_bin, env="conanrun")
