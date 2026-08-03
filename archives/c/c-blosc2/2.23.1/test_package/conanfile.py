#!/usr/bin/env python3
"""Conan test_package — c-blosc2 2.23.1 consumer smoke test.

R34: test calls the blosc2 API (blosc2_compress / blosc2_decompress) and
verifies a compression/decompression round-trip. The L1e destructive negative
test confirms the test genuinely depends on the package.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CBlosc2TestConan(ConanFile):
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
        # R34: run the binary that links against libblosc2 and calls its API.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_c_blosc2")
        self.run(cmd, env="conanrun")
