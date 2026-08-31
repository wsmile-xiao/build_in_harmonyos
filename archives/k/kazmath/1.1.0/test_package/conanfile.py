#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KazmathTestConan(ConanFile):
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
        # Run CTest suite first, then execute the consumer test binary
        CMake(self).test()
        test_binary = os.path.join(self.build_folder, "test_kazmath")
        self.run(test_binary, env="conanrun")
