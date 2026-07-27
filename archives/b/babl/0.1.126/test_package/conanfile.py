#!/usr/bin/env python3
"""Conan test_package for babl 0.1.126."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BablTestConan(ConanFile):
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
        # VirtualRunEnv generates LD_LIBRARY_PATH for the dependency's libdirs.
        # On OHOS it should work since the linker supports LD_LIBRARY_PATH.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_babl"), env="conanrun")
