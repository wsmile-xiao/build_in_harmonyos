#!/usr/bin/env python3
"""Conan test_package for xdelta3 — exercises the library API.

R34: The test substantively calls xd3_encode_memory() and
xd3_decode_memory() to verify the delta compression round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Xdelta3TestConan(ConanFile):
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
        # R34: Run the test binary that calls xd3_encode_memory
        # and xd3_decode_memory for a real encode/decode round-trip.
        bindirs = self.cpp.build.bindirs
        assert bindirs, "No binary output directory found"
        test_bin = os.path.join(bindirs[0], "test_xdelta3")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c '{test_bin}'", env="conanrun")
