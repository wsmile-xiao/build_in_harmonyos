#!/usr/bin/env python3
"""Conan test_package — librtmp/2.4_git20190330 consumer test.

Builds test_librtmp.c against the packaged library and runs it. The test
exercises real API behavior (URL parsing, AMF encode/decode round trips,
log level control, RTMP object lifecycle) with explicit assertions, so a
failure here means the packaged library cannot perform its core functions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrtmpTestConan(ConanFile):
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
        binary = os.path.join(self.cpp.build.bindirs[0], "test_librtmp")
        self.run(f'"{binary}"', env="conanrun")
