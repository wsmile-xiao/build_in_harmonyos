#!/usr/bin/env python3
"""Conan test_package — function2 4.2.3"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Function2TestConan(ConanFile):
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
        # L0d: test() must drive execution via self.run() (not a stub)
        for exe in ("test_function2", "test_function2_hmos"):
            bin_path = os.path.join(self.cpp.build.bindirs[0], exe)
            self.run(bin_path, env="conanrun")