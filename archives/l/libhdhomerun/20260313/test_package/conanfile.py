#!/usr/bin/env python3
"""Conan test_package for libhdhomerun — validates the library API."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibhdhomerunTestConan(ConanFile):
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
        # Sign the test binary for HarmonyOS execution (ELF signing required)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libhdhomerun")
        if os.path.exists(test_bin):
            self.run(f"binary-sign-tool sign -selfSign 1 -inFile {test_bin} -outFile {test_bin} -signAlg SHA256withECDSA", ignore_errors=True)

    def test(self):
        # Run the test binary directly instead of cmake.test()
        # because cmake.test() uses CTest which may fail on HarmonyOS
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libhdhomerun")
        self.run(f'"{test_bin}"', env="conanrun")
