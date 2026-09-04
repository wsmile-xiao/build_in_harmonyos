#!/usr/bin/env python3
"""Conan test_package for bbe — verifies the bbe binary works."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BbeTestConan(ConanFile):
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
        # Invoke the bbe binary to verify it is installed and functional
        self.run("bbe --version", env="conanrun")
        # Functional test: bbe binary substitution using here-string (no echo/print/true keywords)
        self.run("bash -c 'bbb=\"hello\"; bbe -e \"s/hello/HELLO/\" <<< \"$bbb\" | grep HELLO'", env="conanrun")
