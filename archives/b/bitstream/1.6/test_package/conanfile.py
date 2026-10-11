#!/usr/bin/env python3
"""Conan test_package for bitstream 1.6 (header-only).

Compiles and runs test_bitstream.c: builds a synthetic MPEG-TS packet
carrying a PAT section with the library writer API, parses it back with
the reader API and asserts every field round-trips.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

CHECKS = 13


class BitstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_bitstream")
        self.run('"%s"' % bin_path, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "test_bitstream (synthetic TS/PAT parse consumer)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
