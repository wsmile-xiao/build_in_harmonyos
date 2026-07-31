#!/usr/bin/env python3
"""Conan consumer test for Kokkos."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KokkosTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if not can_run(self):
            return
        if not self.cpp.build.bindirs:
            raise ConanInvalidConfiguration("test package has no binary directory")
        binary = os.path.join(self.cpp.build.bindirs[0], "test_kokkos")
        self.run(binary, env="conanrun")
