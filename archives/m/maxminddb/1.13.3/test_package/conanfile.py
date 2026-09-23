#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/maxminddb/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MaxminddbTestConan(ConanFile):
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
        self._decode_test_db()
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_maxminddb')}", env="conanrun")

    def _decode_test_db(self):
        """Decode the base64-text upstream decoder fixture back to binary.

        The .mmdb test database is stored as base64 text in the PR so the
        diff stays text-only (CI checkout-pr `git apply` cannot rebuild
        binary patch data). Reconstruct the exact bytes next to the test
        executable before the consumer test opens it via "data/".
        """
        import base64

        src = os.path.join(self.source_folder, "data", "MaxMind-DB-test-decoder.mmdb.b64")
        dst = os.path.join(self.build_folder, "data", "MaxMind-DB-test-decoder.mmdb")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "r", encoding="ascii") as fh:
            payload = "".join(fh.read().split())
        with open(dst, "wb") as fh:
            fh.write(base64.b64decode(payload))
