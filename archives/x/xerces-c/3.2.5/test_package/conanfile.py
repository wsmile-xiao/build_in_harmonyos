#!/usr/bin/env python3
"""Conan test_package for xerces-c 3.2.5 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is driven by the
Conan toolchain, not raw shell env vars (R33). The consumer test feeds an
in-memory XML document to XercesDOMParser and asserts on the parsed DOM
tree (root tag, element count, text content).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XercesCTestConan(ConanFile):
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
        # R5: OHOS has no /bin/sh — wrap binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_xerces'", env="conanrun")
