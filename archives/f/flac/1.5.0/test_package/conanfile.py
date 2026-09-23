#!/usr/bin/env python3
"""Conan test_package — flac/1.5.0 consumer test (R34: real API round-trip).

Verifies libFLAC links correctly, OGG support is enabled, and the
FLAC__stream_encoder/decoder APIs perform a bit-identical lossless
encode/decode round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FlacTestConan(ConanFile):
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
        # R34: run the test binary that calls real FLAC encoder/decoder APIs
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_flac")
        self.run(cmd, env="conanrun")
