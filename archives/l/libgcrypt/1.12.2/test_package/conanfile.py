#!/usr/bin/env python3
"""Conan consumer test for libgcrypt 1.12.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibgcryptTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross build: consumer execution skipped")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "libgcrypt_consumer")
        cases = (
            "version",
            "sha256",
            "sha512",
            "sha3-256",
            "hmac-sha256",
            "cmac-aes",
            "aes128-ecb-encrypt",
            "aes128-ecb-decrypt",
            "aes256-cbc",
            "chacha20",
            "pbkdf2-sha256",
            "mpi-add",
            "mpi-mod",
            "sexp",
            "nonce",
        )
        for case in cases:
            self.run(
                f'"{test_bin}" {case}',
                env="conanrun",
                cwd=self.build_folder,
            )
