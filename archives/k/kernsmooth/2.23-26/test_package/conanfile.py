#!/usr/bin/env python3
"""test_package for kernsmooth 2.23-26 — R34 substantive numerical test.

The standalone static library ships the KernSmooth Fortran 77 core; the C
test binary below links kernsmooth::kernsmooth and calls real LINPACK/BLAS
routines (linbin_, rlbin_, locpol_) and verifies results numerically.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KernsmoothTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        binary = os.path.join(self.cpp.build.bindirs[0], "test_kernsmooth")
        self.run(binary, env="conanrun")
