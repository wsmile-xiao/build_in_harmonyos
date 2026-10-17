#!/usr/bin/env python3
"""Conan test_package — ipsumdump 1.86 L1 test.

Tests that the ipsumdump binary is installed and functional.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IpsumdumpTestConan(ConanFile):
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
        # Also run a direct self.run() for W3 CI L0d check (R34 negative test)
        self.run("ipsumdump --version", env="conanrun")
