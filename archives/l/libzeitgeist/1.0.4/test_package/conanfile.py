#!/usr/bin/env python3
"""Consumer test for the public Zeitgeist 2.0 API."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibzeitgeistTestConan(ConanFile):
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
        self.run("./test_package", env="conanrun")
