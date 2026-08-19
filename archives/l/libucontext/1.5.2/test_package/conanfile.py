#!/usr/bin/env python3
"""Consumer test for libucontext 1.5.2.

build() compiles the upstream public-domain test_libucontext.c and links it
against the package; test() runs the binary via self.run() (required by the
CI L0d gate: no stub test methods).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibucontextTestConan(ConanFile):
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
        if not can_run(self):
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libucontext")
        self.run(binary, env="conanrun")
