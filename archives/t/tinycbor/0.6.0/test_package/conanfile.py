#!/usr/bin/env python3
"""Conan test_package — consumer verification for tinycbor on OHOS.

R34: the test source calls the real tinycbor public API (encode + parse +
verify) and asserts results; it is not an empty-shell test.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TinycborTestConan(ConanFile):
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
        # Explicitly run the binary so a non-zero exit is observed by CI.
        self.run("./test_tinycbor", env="conanrun")