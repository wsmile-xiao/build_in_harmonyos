#!/usr/bin/env python3
"""Conan test_package — jsonparse-cpp 1.00 L1 official test.

Consumes the installed package through its public headers (parse.h/object.h),
exercising parseJSON/object_toString/object_free and asserting a JSON
round-trip. test() runs the consumer binary via self.run() (L0d: a real
self.run() call is required; CTest alone is treated as a stub).

File location: archives/j/jsonparse-cpp/1.00/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JsonparsecppTestConan(ConanFile):
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
        # L0d: actually run the consumer test binary through self.run() so the
        # test() method is a real execution, not a stub. The binary calls the
        # installed public API (parseJSON/object_toString/object_free) and
        # asserts the JSON round-trip output; it exits non-zero on failure.
        binary = os.path.join(self.cpp.build.bindirs[0], "test_jsonparse-cpp")
        self.run(binary, env="conanrun")
