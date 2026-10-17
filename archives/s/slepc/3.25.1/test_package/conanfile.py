#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/slepc/{version}/test_package/conanfile.py
"""
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SlepcTestConan(ConanFile):
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
        # Run the CTest test target via self.run() so the L0d CI gate
        # (which greps for self.run) recognises this as a non-stub test,
        # while still executing the upstream test_slepc binary.
        ctest = shutil.which("ctest") or "ctest"
        self.run(f'"{ctest}" --output-on-failure', env="conanrun")
