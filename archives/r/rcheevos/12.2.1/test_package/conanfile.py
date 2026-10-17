#!/usr/bin/env python3
"""Conan test_package — rcheevos 12.2.1 (Conan L1 official test).

Consumer test (C): real API assertions (runtime activate/do_frame/triggered,
lboard activation + value formatting, error strings, invalid-input negative
control) against the packaged static library. CI runs this automatically via
`conan create`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RcheevosTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_rcheevos")
        self.run(f'"{exe}"', env="conanrun")
