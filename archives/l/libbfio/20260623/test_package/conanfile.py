#!/usr/bin/env python3
"""Conan test_package — libbfio 20260623 (Conan L1 consumer test).

Builds one C consumer against the installed package and runs it:
test_bfio opens a real file through the public file/handle API and
checks size, sequential read, seek and post-seek content (see test.c).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibbfioTestConan(ConanFile):
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
        # Executed directly rather than through cmake.test(): the CI stub-test
        # gate (L0d) decides on the presence of an explicit execution call in
        # this method.  Running the consumer here also puts its per-check
        # output into the CI log.
        self.run("./test_libbfio", env="conanrun")