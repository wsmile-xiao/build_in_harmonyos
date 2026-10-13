#!/usr/bin/env python3
"""Conan consumer test for utf8proc 2.12.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Utf8ProcTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("Cross build: consumer compiled and linked; target run pending")
            return
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_utf8proc"),
            env="conanrun",
        )
