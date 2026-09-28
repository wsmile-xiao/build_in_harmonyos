#!/usr/bin/env python3
"""Consumer test for cpp-dump 0.7.0 — real API checks via export_var()."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CppDumpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No test binary directory found")
            test_binary = os.path.join(bindirs[0], "test_package")
            if not os.path.isfile(test_binary):
                raise Exception(f"Test binary not found: {test_binary}")
            self.run(test_binary, env="conanrun")
