#!/usr/bin/env python3
"""Conan test_package for libtomfloat — consumer-side API test.

tomfloat.h is a leaky public header: it includes <tommath.h> directly.
The test source therefore consumes libtommath headers transitively, so
libtommath is declared as an explicit test dependency (CMakeDeps emits a
complete config for direct dependencies only).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtomfloatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libtommath/1.3.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the consumer binary directly and assert via its exit code.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libtomfloat"),
            env="conanrun",
        )
