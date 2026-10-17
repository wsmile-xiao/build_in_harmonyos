#!/usr/bin/env python3
"""Conan test_package — spandsp 0.0.6 consumer test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

Location: archives/s/spandsp/0.0.6/test_package/conanfile.py
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpandspTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_spandsp')}", env="conanrun")
