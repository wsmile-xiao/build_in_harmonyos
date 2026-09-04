#!/usr/bin/env python3
"""Conan test_package — brigand 1.3.0 (header-only C++11).

Consumers link `brigand::brigand` (header-only) and run compile-time +
runtime assertions against the installed headers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BrigandTestConan(ConanFile):
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
        # L0d: run the consumer binary explicitly
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_brigand"),
            env="conanrun",
        )