#!/usr/bin/env python3
"""Conan consumer test for EWAHBoolArray 0.8.0.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/ewahboolarray/{version}/test_package/conanfile.py
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EwahboolarrayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # Keep an explicit self.run for the CI L0d/PF3 gate and run the
        # consumer executable through CTest from Conan's build directory.
        self.run("ctest --output-on-failure", cwd=self.build_folder,
                 env="conanrun")
