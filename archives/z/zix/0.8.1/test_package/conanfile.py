#!/usr/bin/env python3
"""Conan test_package for zix 0.8.1."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
        )
