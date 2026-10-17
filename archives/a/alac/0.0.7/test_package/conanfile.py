#!/usr/bin/env python3
"""Test package for alac (cross-compiled to OHOS)."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AlacTestConan(ConanFile):
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
        # Binary can run on aarch64 host (OHOS clang produces arm64 ELF)
        # Run the actual test binary to verify ALAC decoder instantiation
        self.run("./test_package", env="conanrun")
        print("test_package: ALAC decoder instantiation verified (exit code 0)")
        print("ALAC library linked successfully: libALAC.a")