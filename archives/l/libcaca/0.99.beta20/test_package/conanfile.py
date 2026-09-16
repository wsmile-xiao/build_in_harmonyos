#!/usr/bin/env python3
"""Consumer test for libcaca/0.99.beta20.

Builds the C consumer test against the installed package and runs it.  The
program performs real libcaca API calls and asserts on their results, so its
exit code is the test verdict; ctest propagates it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibcacaTestConan(ConanFile):
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
        # ctest-level verdict: the executable is registered with add_test().
        cmake = CMake(self)
        cmake.test()
        # Run it once more directly so the individual assertion results end
        # up in the build log as evidence rather than only on failure.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libcaca"),
                 env="conanrun")
