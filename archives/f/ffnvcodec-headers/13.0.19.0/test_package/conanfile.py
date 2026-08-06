#!/usr/bin/env python3
"""Conan test_package — ffnvcodec-headers 13.0.19.0

Verifies that the NVENC/NVDEC headers are correctly installed and includable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FfnvcodecHeadersTestConan(ConanFile):
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
        # Explicit smoke test: run the binary directly
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_ffnvcodec_headers")
        self.run(cmd, env="conanrun")
