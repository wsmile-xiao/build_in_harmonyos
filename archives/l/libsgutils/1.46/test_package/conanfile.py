#!/usr/bin/env python3
"""Conan test_package — libsgutils 1.46 L1 official test.

Runs the consumer test (test_libsgutils) and the OHOS-specific test
(test_libsgutils_ohos) via ctest, with explicit self.run execution of the
consumer binary as the primary real-execution path (PF3).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsgutilsTestConan(ConanFile):
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
        # 1) Explicit real execution of the consumer binary (PF3)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libsgutils")
        self.run(f"'{test_bin}'", env="conanrun")
        # 2) Also run the OHOS-specific test binary directly
        ohos_bin = os.path.join(self.cpp.build.bindirs[0], "test_libsgutils_ohos")
        self.run(f"'{ohos_bin}'", env="conanrun")
        # 3) ctest over both registered tests
        cmake = CMake(self)
        cmake.test()
