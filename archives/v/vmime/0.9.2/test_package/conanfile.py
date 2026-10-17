#!/usr/bin/env python3
"""Conan test_package for vmime — consumer-side smoke test (L1)."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VmimeTestConan(ConanFile):
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
        # L0d: explicitly run the test binary
        test_bin = os.path.join(self.build_folder, "test_vmime")
        if os.path.exists(test_bin):
            self.run(test_bin, env="conanrun")
