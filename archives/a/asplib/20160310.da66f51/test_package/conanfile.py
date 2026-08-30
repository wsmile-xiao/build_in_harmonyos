#!/usr/bin/env python3
"""Conan test_package — asplib 20160310.da66f51 consumer smoke test.

Builds and runs a real C++ program (test.cpp) that links the installed
asplib static library and exercises its public DSP API:
  - CBiquadFactory: create chained native biquads, set coefficients,
    process samples, verify finite non-zero output
  - CBiquad_Native directly + resetState() (upstream infinite-loop bug
    fixed by the recipe patch)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AsplibTestConan(ConanFile):
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
        # Run the smoke-test binary directly (also runs via CTest below)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_asplib"), env="conanrun")
        cmake = CMake(self)
        cmake.test()
