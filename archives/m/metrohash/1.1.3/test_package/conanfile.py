#!/usr/bin/env python3
"""Conan test_package for metrohash 1.1.3 — Conan L1 official test.

Builds and runs ``test_metrohash`` against the packaged library, verifying a
downstream consumer can find and use MetroHash and that the implementation
reproduces the upstream official verification vectors (src/testvector.h).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MetroHashTestConan(ConanFile):
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
        # Use bash to wrap binary execution where available.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_metrohash'", cwd=self.cpp.build.bindirs[0])
