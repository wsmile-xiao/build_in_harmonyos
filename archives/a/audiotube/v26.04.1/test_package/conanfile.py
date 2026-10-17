#!/usr/bin/env python3
"""Conan test_package for audiotube v26.04.1 — ytm library smoke test.

Verifies that the ytm static library and ytmusic.h header are correctly
packaged and usable by a consumer. The test includes the header, checks
the TESTED_YTMUSICAPI_VERSION constant, and links against libytm.a.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudiotubeTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Run the test binary directly to verify the library is usable
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_audiotube"), env="conanrun")
