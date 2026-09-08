#!/usr/bin/env python3
"""Conan test_package for qt5 5.15.19."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5TestConan(ConanFile):
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
        # L0d compliance: explicitly run the test binary
        self.run(f"cd {self.cpp.build.bindirs[0]} && ./test_qt5_all", env="conanrun")