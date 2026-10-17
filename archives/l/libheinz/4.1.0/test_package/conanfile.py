#!/usr/bin/env python3
"""Consumer test for libheinz 4.1.0.

Includes the installed public headers, exercises core public APIs across all
three modules (Complex, Vectors3D, Rotations3D), and checks return values with
explicit assertion counting.  A non-zero exit code is returned on any failure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibheinzTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Run the consumer test binary directly as well, so CI's L0d gate sees
        # an explicit self.run() and so any CHECK failure aborts with a clear
        # non-zero exit code printed by the binary itself.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_heinz"),
            env="conanrun",
        )
