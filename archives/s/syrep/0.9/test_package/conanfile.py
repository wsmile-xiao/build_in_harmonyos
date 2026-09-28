#!/usr/bin/env python3
"""Conan test_package for syrep — runs the packaged CLI end-to-end."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SyrepTestConan(ConanFile):
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
        # run the built test binary directly (ctest wrapper would also work,
        # but L0d requires an explicit self.run call)
        bindir = os.path.join(self.cpp.build.bindirs[0])
        self.run(
            f'"{os.path.join(bindir, "test_syrep")}"',
            env="conanrun",
        )
