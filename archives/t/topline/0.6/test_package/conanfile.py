"""Conan test_package — consumer behaviour test for the packaged topline binary.

The test runner executes the real `topline` binary with stdout redirected to
a file, lets it run its sampling loop, terminates it and asserts that the
monitor actually produced output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ToplineTestConan(ConanFile):
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
        runner = os.path.join(self.cpp.build.bindirs[0], "test_topline")
        topline_bin = os.path.join(
            self.dependencies["topline"].cpp_info.bindirs[0], "topline"
        )
        self.run(f"{runner} {topline_bin}")
