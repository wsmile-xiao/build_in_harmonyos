#!/usr/bin/env python3
"""Installed-package consumer test for libbrahe 1.3.2.

Builds and runs one program that links against the *packaged* headers and
library and exercises every module the package ships: rounding and
significant digits, GCF/LCM, hyperbolic inverses, log helpers, array
statistics, the PRNG family, integer pretty-printing and sinusoid synthesis
through the simple FFT.

The six upstream console programs in test/ are executed separately by the
recipe's build() step; this program is the installed-package contract check.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("test_libbrahe",)


class LibbraheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException(
                "libbrahe consumer binary cannot run on this platform")
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            self.run(f'"{executable}"', env="conanrun")
