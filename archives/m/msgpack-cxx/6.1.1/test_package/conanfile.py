#!/usr/bin/env python3
"""Conan test_package for msgpack-cxx 6.1.1 — L1 consumer test.

Tests msgpack pack/unpack round-trip with type verification.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MsgpackcxxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"  # Only CMakeDeps in generators; CMakeToolchain in generate()

    def configure(self):
        # Remove os.version if present (header-only lib doesn't need it)
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Fix libcxx mapping: OHOS uses libc++, but CMakeToolchain may generate libstdc++
        # Explicitly remove the default libcxx block to avoid wrong flags
        if self.settings.os == "OHOS":
            tc.blocks.remove("libcxx")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exec = os.path.join(self.cpp.build.bindirs[0], "test_msgpack_cxx")
        self.run(test_exec, env="conanrun")
