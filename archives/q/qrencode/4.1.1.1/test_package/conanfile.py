#!/usr/bin/env python3
"""Conan test_package for qrencode — real consumer API test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/qrencode/4.1.1.1/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QrencodeTestConan(ConanFile):
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
        # Run under Conan's generated runtime environment so shared DLLs resolve.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_qrencode"), env="conanrun")
