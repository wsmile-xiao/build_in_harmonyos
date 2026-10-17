#!/usr/bin/env python3
"""Conan test_package for ELFIO 3.12.

L1 test: verifies the header-only library is correctly installed and usable.
Creates an ELF file, reads it back, and validates ELFIO API behavior.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ElfioTestConan(ConanFile):
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
        # Run the test executable directly to verify ELFIO API works
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_elfio"), env="conanrun")
