#!/usr/bin/env python3
"""Conan test_package for ldns 1.9.0 — L1 official test.

Verifies that the ldns library is properly linked and its API is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ldns headers transitively include openssl headers
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: Run the test binary that calls ldns API
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_ldns')}", env="conanrun")
