#!/usr/bin/env python3
"""Conan test_package — fmi-ls-bus 1.0.0 consumer verification.

Builds a real consumer program against the installed public headers and
runs it. The consumer calls the public fmi-ls-bus C-API (CAN Transmit
operation creation + buffer round-trip) and asserts observable results
(R34: not an empty shell).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FmiLsBusTestConan(ConanFile):
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
        # Run the consumer binary; it returns 0 only when all public-API
        # assertions passed.
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fmi-ls-bus"),
                 env="conanrun")