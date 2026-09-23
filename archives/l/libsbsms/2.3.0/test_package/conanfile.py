#!/usr/bin/env python3
"""Conan test_package — consumer-side verification for libsbsms 2.3.0.

Builds and runs ``test_sbsms.cpp``, which links against the installed package
through CMakeDeps and drives the public API end to end.  Upstream ships no test
suite for 2.3.0 (see ../reports/upstream-test-inventory.md), so this consumer
program is the only executable evidence for the package.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibsbsmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_sbsms")
        self.run(exe, env="conanrun")
