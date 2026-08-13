#!/usr/bin/env python3
"""Conan test_package — Crypt::Bcrypt C library API.

Tests the crypt_blowfish C functions exported from Bcrypt.so:
  - _crypt_blowfish_rn: hash a password and verify
  - _crypt_gensalt_blowfish_rn: generate a salt

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PerlCryptBcryptTestConan(ConanFile):
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
        # Run the C test binary directly (non-zero exit code raises ConanException)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_crypt_bcrypt"), env="conanrun")
