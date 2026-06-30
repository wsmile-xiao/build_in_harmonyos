#!/usr/bin/env python3
"""Conan test_package — AES 0.7.4 (RustCrypto) L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

Since AES 0.7.4 is a pure Rust crate (not directly linkable from C),
this test package uses a standalone C implementation of AES to verify
algorithm correctness on the target platform. The C test program
implements AES-128/192/256 encrypt/decrypt and validates against
NIST FIPS 197 test vectors.

File location: archives/a/aes/0.7.4/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AesTestConan(ConanFile):
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
        # Run the AES verification test binary directly.
        # The test program exits 0 on success, 1 on failure.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_aes"), env="conanrun")
