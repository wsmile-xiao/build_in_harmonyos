#!/usr/bin/env python3
"""Conan test_package for IXWebSocket 12.0.1.

Tests the URL parser API from the IXWebSocket library.
This is the L1 test in the five-level test system.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IxwebsocketTestConan(ConanFile):
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
        # Run the test binary directly to verify the IXWebSocket API works (R34)
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_ixwebsocket")
        self.run(test_binary, env="conanrun")
