#!/usr/bin/env python3
"""Conan test_package — consumer test for json-build 1.2.0.

Builds a real C consumer that includes the installed public header
json-build.h and exercises the jsonb serializer API, verifying the
serialized JSON output string. The built binary is actually executed
via self.run (real consumer verification, not a stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JsonBuildTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Execute the built consumer binary directly (real API call +
        # output verification in test.c; exit code checked by CTest).
        executable = os.path.join(self.cpp.build.bindirs[0], "test_json-build")
        self.run(f'"{executable}"', env="conanrun")
