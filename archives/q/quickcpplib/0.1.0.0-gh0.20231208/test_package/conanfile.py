#!/usr/bin/env python3
"""Conan test_package for quickcpplib 0.1.0.0-gh0.20231208 — Conan L1 official test.

Builds and runs ``test_shim`` against the packaged headers, verifying a
downstream consumer can find and use the quickcpplib unit-test shim API
(CMakeDeps + find_package) through real assertions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class QuickcpplibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_shim'", cwd=self.cpp.build.bindirs[0])
