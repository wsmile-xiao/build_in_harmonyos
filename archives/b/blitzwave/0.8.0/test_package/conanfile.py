#!/usr/bin/env python3
"""Conan test_package for blitzwave/0.8.0 — L1 consumer test.

Builds a real downstream consumer against the packaged blitzwave (and the
blitz headers its public headers pull in) and executes the binary directly
with self.run(..., env="conanrun").
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BlitzwaveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # blitz is a transitive *header* dependency: blitzwave/Wavelet.h
        # includes <blitz/array.h>.  CMakeDeps does not fill include dirs
        # for transitive dependencies, so the consumer must require blitz
        # explicitly to get blitz::blitz include dirs.
        self.requires("blitz/1.0.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_blitzwave")
        self.run(f'"{binary}"', env="conanrun")
