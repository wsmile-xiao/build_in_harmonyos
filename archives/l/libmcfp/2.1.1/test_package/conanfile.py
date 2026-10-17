#!/usr/bin/env python3
"""Conan test_package — libmcfp 2.1.1"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmcfpTestConan(ConanFile):
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
        # Run the consumer binary built in build().  test.cpp drives the real
        # mcfp parsing API on device (parse -n 7 --text hello, assert num==7 &&
        # text=="hello" and vector collection) and returns 0 on success.
        # L0d gate requires a literal self.run() in test() (CI L0d rejects a
        # bare cmake.test() as a possible stub).
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libmcfp"),
            env="conanrun",
        )
