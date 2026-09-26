#!/usr/bin/env python3
"""test_package — bitmapplusplus 1.1.1 consumer test.

Real consumer verification: builds a C++17 program that uses the installed
public header bmp::BitmapPlusPlus (via the exported CMake target
bmp::BitmapPlusPlus) and exercises real API behaviours (construct, fill,
index, save, load round-trip, width/height, iteration). Each assertion that
fails returns exit-code 1. Also builds/runs an OHOS-specific test that
verifies the BMP read/write round-trip under the OHOS runtime (writable
TMPDIR semantics, real file I/O).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BitmapplusplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found")
            for bin_name in ("test_bitmapplusplus", "test_bitmapplusplus_ohos"):
                bin_path = os.path.join(bindirs[0], bin_name)
                if not os.path.isfile(bin_path):
                    raise Exception(f"Test binary not found: {bin_path}")
                self.run(bin_path, env="conanrun")