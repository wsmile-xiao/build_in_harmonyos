#!/usr/bin/env python3
"""Conan test_package for mosquitto — verifies the library API is callable."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MosquittoTestConan(ConanFile):
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
        # Run the test binary directly with conanrun env to ensure
        # LD_LIBRARY_PATH is properly set for shared library resolution
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_mosquitto')}", env="conanrun")
