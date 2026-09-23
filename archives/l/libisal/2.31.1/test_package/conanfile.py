#!/usr/bin/env python3
"""Conan test_package for libisal 2.31.1.

Consumer test (test.c): known-answer CRC checks (crc16_t10dif, crc32_ieee,
crc32_gzip_refl, crc32_iscsi, crc64_ecma_norm, crc64_jones_norm), an igzip
stateless deflate/inflate round-trip over 64 KiB with Adler-32 cross-check,
a raid xor_gen parity check and an erasure_code gf_vect_mul check against a
bitwise GF(2^8) reference — 13 assertions in total.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibisalTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libisal"),
                 env="conanrun")
