#!/usr/bin/env python3
"""Consumer test for libMeshb 8.02."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmeshbTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        for name in ("test_libmeshb_consumer", "test_libmeshb_ohos"):
            self.run(os.path.join(bindir, name), env="conanrun")
