#!/usr/bin/env python3
"""Consumer test package for swiftshader 0_git20260921."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SwiftShaderTestConan(ConanFile):
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
        # Runs the consumer binary which drives a full Vulkan compute workload
        # through the installed SwiftShader ICD.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_swiftshader"),
            env="conanrun",
        )
