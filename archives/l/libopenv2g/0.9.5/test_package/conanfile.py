#!/usr/bin/env python3
"""Consumer-side Conan test for libopenv2g 0.9.5."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libopenv2gTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libopenv2g")
        self.run(binary, env="conanrun", cwd=self.build_folder)
