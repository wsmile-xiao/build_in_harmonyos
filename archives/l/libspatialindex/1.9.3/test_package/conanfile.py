#!/usr/bin/env python3
"""Consumer test package - libspatialindex (real C API calls)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibspatialindexTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_consumer")
        self.run(f"\"{bin_path}\"", env="conanrun", cwd=self.build_folder)
