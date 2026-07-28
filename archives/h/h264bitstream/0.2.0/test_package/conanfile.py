#!/usr/bin/env python3
"""Conan test_package — h264bitstream 0.2.0

L1 test: verify the library can be linked and h264_analyze binary works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class H264BitstreamTestConan(ConanFile):
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
        # Run the API test binary
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_h264bitstream")
        self.run(f"{test_bin}", env="conanrun")
        # Functional test: run h264_analyze on a minimal H.264 bitstream
        # (h264_analyze -h returns exit code 1 due to upstream bug, so test with real input)
        bin_dir = self.dependencies["h264bitstream"].cpp_info.bindirs[0]
        h264_analyze = os.path.join(bin_dir, "h264_analyze")
        # Minimal H.264 Annex B bitstream: start code + SPS NAL unit
        test_h264 = os.path.join(self.build_folder, "test.h264")
        with open(test_h264, "wb") as f:
            f.write(bytes.fromhex("0000000167" "42000af80a69a0"))
        self.run(f'"{h264_analyze}" "{test_h264}"', env="conanrun")
