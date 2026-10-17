#!/usr/bin/env python3
"""Conan test_package — libtheora/1.2.0-alpha1 consumer test (R34).

Real encode->decode round-trip through the packaged theoraenc/theoradec
libraries: 4 frames of 32x32 YUV420 video encoded with th_encode_*,
decoded back with th_decode_*, verifying frame count, picture
dimensions, comment propagation and approximate pixel fidelity.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtheoraTestConan(ConanFile):
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
        # R34: run the test binary that calls real theora encoder and
        # decoder APIs against the installed package.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_theora")
        self.run(cmd, env="conanrun")
