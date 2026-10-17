#!/usr/bin/env python3
"""Consumer test for libxls 1.6.3."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibxlsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if not can_run(self):
            self.output.info("Cross-building: consumer executable compiled and linked")
            return
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libxls")
        self.run(test_binary, env="conanrun")
